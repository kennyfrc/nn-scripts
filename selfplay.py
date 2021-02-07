# library for cli
import argparse
# libraries for general pgn writing and uci comms
import chess
import chess.pgn
import chess.engine
# libraries for move picker
import chess.polyglot
import random
import math
# libaries to complete 7 tag roster
import socket
import datetime
# utilities
import os
import os.path
from os import path
import pdb

# threshholds
WIN_THRESHOLD = 100

def parse_result(result_str, board) -> int:
    assert board.is_valid(), "Invalid board."

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

def game_sanity_check(game) -> bool:
    assert game.board().is_valid(), "Invalid board."

    if not game.headers["Result"] in ["1/2-1/2", "0-1", "1-0"]:
        print("invalid result", game.headers["Result"])
        return False
    return True

def parse_game(game, writer) -> None:
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

def pick_randomly(results) -> tuple:
    result = random.choices(results)
    return result[0]['pv'][0], result[0]["score"]
    
def pick_with_softmax(results, color) -> tuple:
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

def pick_bestmove(results) -> tuple:
    return results[0]["pv"][0], results[0]["score"]

def play(games, engine, file_type, nodes, depth, multipv, mode, file_name, cutoff_move, book_reader) -> None:
    # intialize options
    if nodes == 0:
        nodes = None
    if depth == 0:
        depth = None

    # default if you don't set anything
    if nodes == None and depth == None:
        nodes = 1

    # to log results
    white_wins = 0
    black_wins = 0
    draws = 0

    # initialize engines
    engine_w = chess.engine.SimpleEngine.popen_uci(engine)
    engine_b = chess.engine.SimpleEngine.popen_uci(engine)

    for i in range(1, games+1):
        if i % 10 == 0 or i == 1 or i == games:
            print(f"Playing: game {i} out of {games}")
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
            # for random mover or book move
            root_moves = None
            # book move
            book_move = None

            # probe book
            # set multipv to none when using book move
            if book_reader:
                entries = list(book_reader.find_all(board))
                if list(entries) != []:
                    book_move = random.choices(list(entries))[0].move
                    root_moves = []
                    root_moves.append(book_move)
                    multipv = 1
                    assert root_moves, "Book move not read."
            
            # if off book and the mode is random, choose a random move
            # set multipv to none when using random move
            if root_moves and mode == "random" and board.fullmove_number < cutoff_move:
                random_move = random.choices(list(board.legal_moves))
                root_moves = []
                root_moves.append(random_move[0])
                multipv = 1
                assert root_moves, "Random move not found."

            # define non-book move
            if board.turn == chess.WHITE:
                results = engine_w.analyse(board, chess.engine.Limit(nodes=nodes, depth=depth), info=chess.engine.Info.ALL, multipv=multipv, root_moves=root_moves)

                assert results[0]["score"].relative.score() != None or results[0]["score"].is_mate(), "Score or mate can't be found for engine on white side."
            else:
                results = engine_b.analyse(board, chess.engine.Limit(nodes=nodes, depth=depth), info=chess.engine.Info.ALL, multipv=multipv,root_moves=root_moves)

                assert results[0]["score"].relative.score() != None or results[0]["score"].is_mate(), "Score or mate can't be found for engine on black side."

            if board.fullmove_number > cutoff_move:
                move, povscore = pick_bestmove(results)
            elif mode == "softmax":
                move, povscore = pick_with_softmax(results, board.turn)
            else:
                move, povscore = pick_randomly(results)

            # play the move
            board.push(move)

            assert board.is_valid(), "Invalid move."

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
                        white_wins += 1
                    else:
                        game.headers['Result'] = "0-1"
                        black_wins += 1

                # write non-checkmate eval
                else:
                    score = povscore.relative.score(mate_score=32000)

                    assert score != None, "Invalid score."
                    
                    if (score <= WIN_THRESHOLD and score >= -WIN_THRESHOLD) or board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition():
                        game.headers['Result'] = "1/2-1/2"
                        draws += 1
                    elif (score < -WIN_THRESHOLD):
                        game.headers['Result'] = "0-1"
                        black_wins += 1
                    elif (score > WIN_THRESHOLD):
                        game.headers['Result'] = "1-0"
                        white_wins += 1

                assert (draws + white_wins + black_wins) == i, "Results don't add up to total game count."

            # for debugging
            # print(game)

        # write games

        if file_type == "plain": 
            output_file = open(file_name, 'a+')
            parse_game(game, output_file)
            output_file.close()

            assert path.exists(file_name), "Couldn't create .plain file."

        elif file_type == "pgn":
            print(game, file=open(file_name, "a+"), end="\n\n")

            assert path.exists(file_name), "Couldn't create .pgn file."


    # exit book
    book_reader.close()

    # exit engines
    engine_w.quit()
    engine_b.quit()

    # log results
    print(f"white win rate: {round(white_wins / games * 100,2)}%")
    print(f"black win rate: {round(black_wins / games * 100,2)}%")
    print(f"draw rate: {round(draws / games * 100,2)}%")

def main() -> None:
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, required=True)
    parser.add_argument("--engine", type=str, default="lc0")
    parser.add_argument("--file_type", type=str, default="pgn", choices=["pgn", "plain"])
    parser.add_argument("--nodes", type=int, default=0)
    parser.add_argument("--depth", type=int, default=0)
    parser.add_argument("--multipv", type=int, default=1)
    parser.add_argument("--mode", type=str, default="random", choices=["softmax", "random", "random-multipv"])
    parser.add_argument("--cutoff", type=int, default=30)
    parser.add_argument("--book", type=str)

    # initialize options
    args = parser.parse_args()

    assert args.games >= 1, "Choose a game count greater than 1"
    assert args.nodes >= 0, "Use a non-negative node count."
    assert args.depth >= 0, "Use a non-negative depth count."
    assert args.multipv > 0, "Use a positive multipv count."
    assert args.cutoff > 0, "Use a positive cutoff count."
    assert path.exists(args.book), "Can't find book. Kindly check the path."

    games = args.games
    engine = args.engine
    file_type = args.file_type
    nodes = args.nodes
    depth = args.depth
    multipv = args.multipv if (args.multipv > 1 and (args.mode == "random-multipv" or args.mode == "softmax")) else 10
    mode = args.mode
    cutoff_move = args.cutoff
    base_name = "games-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    file_name = base_name + ".pgn" if file_type == "pgn" else base_name + ".plain"

    # initialize book
    if args.book:
        reader = chess.polyglot.open_reader(args.book)
        if reader:
            print(f"BOOK:", args.book)
    else:
        reader = None
        print(f"BOOK: Using no book")

    # print the options you've set
    print(f"NUM OF GAMES:", games)
    print(f"ENGINE:", engine)
    print(f"NODES:", nodes)
    print(f"DEPTH:", depth)
    print(f"MULTIPV:", multipv)
    print(f"MODE:", mode)
    print(f"FILE_TYPE:", file_type)
    print(f"CUTOFF BY MOVE:", cutoff_move)
    print(f"OUTPUT_NAME:", file_name)

    # run self-play games
    play(games, engine, file_type, nodes, depth, multipv, mode, file_name, cutoff_move, reader)

    print(f"Done!")

if __name__ == "__main__":
    main()
