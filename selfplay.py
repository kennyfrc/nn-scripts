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

# for .plain
# highest observed from sf gensfen is 3875
MAX_EVAL = 3875

# parse result of game
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

# check if the game isn't botched
def game_sanity_check(game) -> bool:
    assert game.board().is_valid(), "Invalid board."

    if not game.headers["Result"] in ["1/2-1/2", "0-1", "1-0"]:
        print("invalid result", game.headers["Result"])
        return False
    return True

def clamp(score, minimum=-MAX_EVAL, maximum=MAX_EVAL):
    return max(minimum, min(score, maximum))

# scale score between [-MAX_EVAL, MAX_EVAL]
# for nnue trainer compatibility
def gensfen_eval(score, game_progress):
    # exponential formulas based on
    # game progress and known win cps based on game phase

    mg_known_win = 1034.96*math.exp(-1.43687*game_progress)
    assert mg_known_win >= 245 and mg_known_win <= 1035

    mg_scaled_eval = int(clamp(score/mg_known_win * MAX_EVAL))
    assert mg_scaled_eval >= -MAX_EVAL and mg_scaled_eval <= MAX_EVAL

    eg_known_win = 300*math.exp(-1.09861*game_progress)
    assert eg_known_win >= 85 and eg_known_win <= 350

    eg_scaled_eval = int(clamp(score/eg_known_win * MAX_EVAL))
    assert eg_scaled_eval >= -MAX_EVAL and eg_scaled_eval <= MAX_EVAL

    scaled_eval = int((1-game_progress)*mg_scaled_eval+((game_progress)*eg_scaled_eval))
    assert scaled_eval >= -MAX_EVAL and scaled_eval <= MAX_EVAL

    return scaled_eval

# parse to stockfish nnue format
def parse_game(game, writer, min_ply) -> None:
    if not game_sanity_check(game):
        return

    result: str = game.headers["Result"]

    node = game.end()
    end_ply = node.ply()
    while node.move != None:
        # stockfish nnue is sensitive to low evals, thus skip it unless it exceeds min_ply
        if node.ply() < min_ply:
            node = node.parent
            continue

        game_progress = node.ply() / end_ply

        assert game_progress >= 0 and game_progress <= 1

        # stockfish trainer format
        move = node.move
        comment: str = node.comment
        writer.write("fen " + node.parent.board().fen() + "\n")
        writer.write("move " + str(move) + "\n")

        if node.parent.turn() == chess.WHITE:
            score = node.eval().pov(chess.WHITE).score(mate_score=1500)

            scaled_score = gensfen_eval(score, game_progress)

            writer.write("score " + str(int(scaled_score)) + "\n")
            writer.write("ply " + str(node.ply())+"\n")        
            writer.write("result " + str(parse_result(result, node.parent.board())) +"\n")
        else:
            score = node.eval().pov(chess.BLACK).score(mate_score=1500)

            scaled_score = gensfen_eval(score, game_progress)

            writer.write("score " + str(int(scaled_score)) + "\n")
            writer.write("ply " + str(node.ply())+"\n")        
            writer.write("result " + str(parse_result(result, node.parent.board())) +"\n")
        writer.write("e\n")
        node = node.parent

# pick random move
def pick_randomly(results) -> tuple:
    result = random.choices(results)
    return result[0]['pv'][0], result[0]["score"]

# check if policy sums to 1
def check_policy_sum(policies) -> bool:
    sum_check = 0
    for policy in policies:
        sum_check += policy
    if sum_check >= 0.99 and sum_check <= 1.01:
        return True
    else:
        return False
    
# pick a move by softmaxing over multipv: https://en.wikipedia.org/wiki/Softmax_function
def pick_with_softmax(results, color) -> tuple:
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

    assert check_policy_sum(final_policies), "Policy sum does not approximate to 1."

    # relate move with score
    moves_wscore = list(zip(moves, scores))

    # randomly sample move (weighted)
    final_move_wscore = random.choices(moves_wscore, weights=final_policies, k=1)[0]

    return final_move_wscore[0][0], final_move_wscore[1]

# get best move from principal variation
def pick_bestmove(results) -> tuple:
    return results[0]["pv"][0], results[0]["score"]

# initiate self-play games
def play(games, engine, file_type, nodes, depth, multipv, mode, file_name, book_reader, min_ply) -> None:
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

        # log status
        if i % 10 == 0 or i == 1 or i == games:
            print(f"Playing: game {i} out of {games}")
        
        # init game tree
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
            
            # holds all variations
            results = None

            # holds list of random moves or book moves for python-chess
            root_moves = None

            # actual book move state
            book_move = None

            # probe book
            if book_reader:
                entries = list(book_reader.find_all(board))
                if list(entries) != []:
                    book_move = random.choices(list(entries))[0].move
                    root_moves = []
                    root_moves.append(book_move)
                    multipv = 1
                    assert root_moves, "Book move not read."
            
            # if off-book and the mode is random, choose a random move
            if root_moves and mode == "random" and board.fullmove_number <= min_ply/2:
                random_move = random.choices(list(board.legal_moves))
                root_moves = []
                root_moves.append(random_move[0])
                multipv = 1
                assert root_moves, "Random move not found."

            # engine to define UCI move and score for given book, multipv, and mode
            if board.turn == chess.WHITE:
                results = engine_w.analyse(board, chess.engine.Limit(nodes=nodes, depth=depth), info=chess.engine.Info.ALL, multipv=multipv, root_moves=root_moves)

                assert results[0]["score"].relative.score() != None or results[0]["score"].is_mate(), "Score or mate can't be found for engine on white side."
            else:
                results = engine_b.analyse(board, chess.engine.Limit(nodes=nodes, depth=depth), info=chess.engine.Info.ALL, multipv=multipv,root_moves=root_moves)

                assert results[0]["score"].relative.score() != None or results[0]["score"].is_mate(), "Score or mate can't be found for engine on black side."

            # pick move from variations given user options
            if board.fullmove_number > min_ply/2:
                move, povscore = pick_bestmove(results)
            elif mode == "softmax":
                move, povscore = pick_with_softmax(results, board.turn)
            else:
                move, povscore = pick_randomly(results)

            # apply the move to the board data structure
            board.push(move)

            assert board.is_valid(), "Invalid move."

            # write the move in the game tree (for pgn / plain)
            if(node == None):
                node = game.add_main_variation(move)
            else:
                node = node.add_main_variation(move)

            # write the score in the game tree
            node.set_eval(povscore)

            # write the result in the game tree if game is over
            if board.is_game_over():
                # results for checkmate
                if board.is_checkmate():
                    if node.parent.turn() == chess.WHITE:
                        game.headers['Result'] = "1-0"
                        white_wins += 1
                    else:
                        game.headers['Result'] = "0-1"
                        black_wins += 1

                # results for non-checkmate
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

        # write game tree to file
        if file_type == "plain":
            output_file = open(file_name, 'a+')
            parse_game(game, output_file, min_ply)
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
    parser.add_argument("--book", type=str)
    parser.add_argument("--min_ply", type=int, default=15)

    # initialize arguments
    args = parser.parse_args()

    games = args.games
    engine = args.engine
    file_type = args.file_type
    nodes = args.nodes
    depth = args.depth
    multipv = args.multipv if (args.multipv > 1 and (args.mode == "random-multipv" or args.mode == "softmax")) else 10
    mode = args.mode
    base_name = "games-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    file_name = base_name + ".pgn" if file_type == "pgn" else base_name + ".plain"
    min_ply = args.min_ply

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
    print(f"OUTPUT_NAME:", file_name)

    # run self-play games
    play(games, engine, file_type, nodes, depth, multipv, mode, file_name, reader, min_ply)

    print(f"Done!")

if __name__ == "__main__":
    main()
