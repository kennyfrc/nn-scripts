import chess
import chess.pgn
import chess.engine
import chess.polyglot
import random
import pdb
import math

# define engines
ENGINE_1="lc0"
ENGINE_2="lc0"

# threshholds
WIN_THRESHOLD = 100

# engine options
MULTIPV = 10
NODES = 1
BOOK_MIN_PLY = 4 

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

def main():
    # initialize engines
    engine_w = chess.engine.SimpleEngine.popen_uci(ENGINE_1)
    engine_b = chess.engine.SimpleEngine.popen_uci(ENGINE_2)

    # create game tree
    game = chess.pgn.Game()
    game.headers["Event"] = "Example"
    game.headers["White"] = ENGINE_1
    game.headers["Black"] = ENGINE_2
    # init game node
    node = None

    # initialize board
    board = chess.Board()


    while not board.is_game_over():
        # init engine moves
        results = None

        # if we're in the opening use the book
        if board.ply() <= BOOK_MIN_PLY-1:
            # init book
            book = None
            # load polyglot
            with chess.polyglot.open_reader("books/jbook_4ply.bin") as opening_book:
                if opening_book.get(board):
                    book = opening_book.weighted_choice(board)
            
            # define and evaluate book move
            # chess.engine.Info(2) == cp score 
            if board.turn == chess.WHITE:
                results = engine_w.analyse(board, chess.engine.Limit(nodes=NODES), info=chess.engine.Info.ALL, multipv=MULTIPV, root_moves=[book.move])
            else:
                results = engine_b.analyse(board, chess.engine.Limit(nodes=NODES), info=chess.engine.Info.ALL, multipv=MULTIPV, root_moves=[book.move])

            opening_book.close()
        # else, use engine moves
        else:
            # define non-book move
            # chess.engine.Info(2) == cp score 
            if board.turn == chess.WHITE:
                results = engine_w.analyse(board, chess.engine.Limit(nodes=NODES), info=chess.engine.Info.ALL, multipv=MULTIPV)
            else:
                results = engine_b.analyse(board, chess.engine.Limit(nodes=NODES), info=chess.engine.Info.ALL, multipv=MULTIPV)

        move, score = pick_with_softmax(results,board.turn)

        # play the move
        board.push(move)

        # record the move in the game tree
        if(node == None):
            node = game.add_main_variation(move)
            
        else:
            node = node.add_main_variation(move)

        # write score
        povscore = score
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

                if (score <= WIN_THRESHOLD and score >= -WIN_THRESHOLD):
                    game.headers['Result'] = "1/2-1/2"
                elif (score < -WIN_THRESHOLD):
                    game.headers['Result'] = "0-1"
                elif (score > WIN_THRESHOLD):
                    game.headers['Result'] = "1-0"

        # for debugging
        # print(game)

    # exit engines
    engine_w.quit()
    engine_b.quit()

    # write to a file
    print(game, file=open("test.pgn", "w"), end="\n\n")


main()