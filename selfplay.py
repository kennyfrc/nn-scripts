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

# define engines
ENGINE_1="lc0"
ENGINE_2="lc0"

# threshholds
WIN_THRESHOLD = 100

# engine options
MULTIPV = 10
NODES = 1
DEPTH = 8

# filenames
BUFFER_FILE = "buffer.pgn"
MAIN_FILE = "main.pgn"

# number of games
GAMES = 10000

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


def main(games):
    # initialize engines
    engine_w = chess.engine.SimpleEngine.popen_uci(ENGINE_1)
    engine_b = chess.engine.SimpleEngine.popen_uci(ENGINE_2)

    for i in range(1, games+1):
        print(f"playing: game {i} out of {games}")
        # create game tree
        game = chess.pgn.Game()
        game.headers["White"] = ENGINE_1
        game.headers["Black"] = ENGINE_2
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
                results = engine_w.analyse(board, chess.engine.Limit(nodes=NODES), info=chess.engine.Info.ALL, multipv=MULTIPV)
            else:
                results = engine_b.analyse(board, chess.engine.Limit(nodes=NODES), info=chess.engine.Info.ALL, multipv=MULTIPV)

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

        # write to a file
        print(game, file=open(BUFFER_FILE, "w"), end="\n\n")

        # concatenate to main pgn
        fin = open(BUFFER_FILE, "r")
        buffer_file = fin.read()
        fin.close()

        fout = open(MAIN_FILE, "a")
        fout.write(buffer_file)
        fout.close()

        os.remove("buffer.pgn")

    # exit engines
    engine_w.quit()
    engine_b.quit()

main(GAMES)