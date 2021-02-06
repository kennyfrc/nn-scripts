# library for cli
import argparse
# libraries for general pgn writing and uci comms
import chess
import chess.pgn
import chess.engine
# libraries for move picker
import random
import math
# libaries to complete 7 tag roster
import socket
import datetime
# library to remove buffer file at the end
import os

# threshholds
WIN_THRESHOLD = 100

# filenames
OUTPUT_PGN = "output.pgn"
OUTPUT_PLAIN = "output.plain"

def parse_result(result_str:str, board:chess.Board) -> int:
    if result_str == "1/2-1/2":
        return 0
    if result_str == "0-1":
        if board.turn == chess.WHITE:
            return -1
        else:
            return 1
    elif result_str == "1-0":
        if board.turn == chess.WHITE:
            return 1
        else:
            return -1
    else:
        print("illegal result", result_str)
        raise ValueError

def game_sanity_check(game: chess.pgn.Game) -> bool:
    if not game.headers["Result"] in ["1/2-1/2", "0-1", "1-0"]:
        print("invalid result", game.headers["Result"])
        return False
    return True

def parse_game(game: chess.pgn.Game, writer)->None:
    if not game_sanity_check(game):
        return

    result: str = game.headers["Result"]

    node = game.end()
    while node.move != None:
        move = node.move
        comment: str = node.comment
        writer.write("fen " + node.parent.board().fen() + "\n")
        writer.write("move " + str(move) + "\n")
        if node.parent.turn() == chess.WHITE:
            writer.write("score " + str(int(node.eval().pov(chess.WHITE).score(mate_score=15000)*2.08)) + "\n")
            writer.write("ply " + str(node.ply())+"\n")        
            writer.write("result " + str(parse_result(result, node.parent.board())) +"\n")
        else:
            writer.write("score " + str(int(node.eval().pov(chess.BLACK).score(mate_score=15000)*2.08)) + "\n")
            writer.write("ply " + str(node.ply())+"\n")        
            writer.write("result " + str(parse_result(result, node.parent.board())) +"\n")
        writer.write("e\n")
        node = node.parent

def pick_with_softmax(results, color):
    # softmax allows us to pick moves randomly
    # based upon the likelihood its the best move
    # https://en.wikipedia.org/wiki/Softmax_function
    scores = []
    policies = []
    policy_sum = 0
    moves = []

    # define the softmax numerator and also append the moves
    if color == chess.WHITE:
        for result in results:
            # convert leela mate score of None to 0
            # also turn ultra tiny values to 0 to avoid overflow errors with math.exp
            raw_score = None
            if result["score"].relative.score() != None and result["score"].relative.score() >= -0.01 and result["score"].relative.score() <= 0.01:
                raw_score = result["score"].relative.score()
            else:
                raw_score = 0
            policies.append(math.exp(raw_score))
            scores.append(result["score"])
            moves.append(result["pv"])
    else:
        for result in results:
            raw_score = None
            if result["score"].relative.score() != None and result["score"].relative.score() >= -0.01 and result["score"].relative.score() <= 0.01:
                raw_score = result["score"].relative.score()
            else:
                raw_score = 0
            policies.append(-math.exp(raw_score))
            scores.append(result["score"])
            moves.append(result["pv"])

    # get the denominator of the softmax function
    for policy in policies:
        policy_sum += policy

    final_policies = list(map(lambda pol: pol/policy_sum, policies))

    # for debugging
    # sum_check = 0
    # for policy in final_policies:
    #     sum_check += policy
    # print(f"policy_sum:", sum_check)

    # relate move with score
    moves_wscore = list(zip(moves, scores))

    # randomly sample move
    final_move_wscore = random.choices(moves_wscore, weights=final_policies, k=1)[0]

    # return move and score
    return final_move_wscore[0][0], final_move_wscore[1]

def pick_bestmove(results):
    return results[0]["pv"][0], results[0]["score"]


def play(games, engine, file_type, nodes, depth, multipv):
    # intialize options
    if nodes == 0:
        nodes = None
    if depth == 0:
        depth = None

    # default if you don't set anything
    if nodes == None and depth == None:
        nodes = 1

    print(f"nodes:", nodes)
    print(f"depth:", depth)

    # initialize engines
    engine_w = chess.engine.SimpleEngine.popen_uci(engine)
    engine_b = chess.engine.SimpleEngine.popen_uci(engine)

    for i in range(1, games+1):
        print(f"playing: game {i} out of {games}")
        # create game tree
        game = chess.pgn.Game()
        game.headers["White"] = engine
        game.headers["Black"] = engine
        game.headers["Round"] = i
        game.headers["Date"] = datetime.date.today().strftime("%Y.%m.%d")
        game.headers["Site"] = socket.gethostname()
        game.headers["Event"] = f"Game Generation"
        # init game node
        node = None

        # initialize board
        board = chess.Board()

        while not board.is_game_over():
            # init engine moves
            results = None

            # define non-book move
            # chess.engine.Info(2) == cp score 
            if board.turn == chess.WHITE:
                results = engine_w.analyse(board, chess.engine.Limit(nodes=nodes,depth=depth), info=chess.engine.Info.ALL, multipv=multipv)
            else:
                results = engine_b.analyse(board, chess.engine.Limit(nodes=nodes,depth=depth), info=chess.engine.Info.ALL, multipv=multipv)

            if board.fullmove_number > 30:
                move, povscore = pick_bestmove(results)
            else:
                move, povscore = pick_with_softmax(results,board.turn)

            # play the move
            board.push(move)

            # record the move in the game tree
            if(node == None):
                node = game.add_main_variation(move)
                
            else:
                node = node.add_main_variation(move)

            # write score
            node.set_eval(povscore)

            # write result
            if board.is_game_over():
                # write checkmate
                if board.is_checkmate():
                    if node.parent.turn() == chess.WHITE:
                        game.headers['Result'] = "1-0"
                    else:
                        game.headers['Result'] = "0-1"

                # write non-checkmate eval
                else:
                    score = povscore.relative.score()

                    if (score <= WIN_THRESHOLD and score >= -WIN_THRESHOLD) or board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
                        game.headers['Result'] = "1/2-1/2"
                    elif (score < -WIN_THRESHOLD):
                        game.headers['Result'] = "0-1"
                    elif (score > WIN_THRESHOLD):
                        game.headers['Result'] = "1-0"

            # for debugging
            # print(game)

        # write games
        if file_type == "plain": 
            output_file = open(OUTPUT_PLAIN, 'w')
            parse_game(game, output_file)
            output_file.close()
        elif file_type == "pgn":
            print(game, file=open(OUTPUT_PGN, "a+"), end="\n\n")

    # exit engines
    engine_w.quit()
    engine_b.quit()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, required=True)
    parser.add_argument("--engine", type=str, default="lc0")
    parser.add_argument("--output", type=str, default="pgn")
    parser.add_argument("--nodes", type=int, default=0)
    parser.add_argument("--depth", type=int, default=0)
    parser.add_argument("--multipv", type=int, default=1)
    args = parser.parse_args()
    games = args.games
    engine = args.engine
    file_type = args.output
    nodes = args.nodes
    depth = args.depth
    multipv = args.multipv

    play(games, engine, file_type, nodes, depth, multipv)

if __name__ == "__main__":
    main()