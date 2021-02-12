import chess
import datetime
import argparse
import math
import os
import os.path
from os import path
import pdb


# highest observed from sf is 3875
MAX_EVAL = 3875

# clamp values between -3200 to 3200 for the nnue tapered eval
def clamp(x, minimum=-MAX_EVAL, maximum=MAX_EVAL):
    return max(minimum, min(x, maximum))

# scaling idea - leela - didn't learn anything
# leela probability [-1 to 1]
# def Q(score, scale=100):
#     return round(0.640177*math.atan(0.00895138*score/scale*100),2)

# scaling idea - sf - doesn't make intuitive sense
# stockfish win rate model
# assumes you're passing internal units
# def win_rate_model(value, ply):
#     # model only covers 240 plies
#     m = min(240, ply) / 64

#     # Coefficients of a 3rd order polynomial fit based on fishtest data
#     # for two parameters needed to transform eval to the argument of a
#     # logistic function.
#     as_arr = [-8.24404295, 64.23892342, -95.73056462, 153.86478679]
#     bs_arr = [-3.37154371, 28.44489198, -56.67657741,  72.05858751]
#     a = (((as_arr[0] * m + as_arr[1]) * m + as_arr[2]) * m) + as_arr[3]
#     b = (((bs_arr[0] * m + bs_arr[1]) * m + bs_arr[2]) * m) + bs_arr[3]

#     # Transform eval to centipawns
#     x = clamp(value / 2.08, -1000, 1000)

#     # Return win rate as percentage
#     return round((((0.5 + 1000 / (1 + math.exp((a - x) / b)))/1000)-0.5)*2,2)

def main() -> None:
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True)
    parser.add_argument("--scale", type=int, default=100)

    # set arguments
    args = parser.parse_args()
    file = args.file
    scale = args.scale

    # load current file
    plain_file = open(file, "r")

    # define name of file to write on
    file_name = "fix-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".plain"

    # load file to write on
    output_file = open(file_name, 'a+')
    assert path.exists(file_name), "Couldn't create .plain file."

    # set preconditions
    past_ply = 0
    positions = 0

    position = {
        'fen': None,
        'move': None,
        'score': None,
        'ply': None,
        'result': ''
    }

    for line in plain_file:
        values = line.split()

        if values[0] == "fen":
            fen = " ".join(values[1:])
            position["fen"] = fen

            assert chess.Board(fen=fen).is_valid()

        if values[0] == "move":
            position["move"] = values[1]

            assert position["move"] != None

        if values[0] == "score":
            position["score"] = int(values[1])

            assert position["score"] != None

        if values[0] == "ply":
            current_ply = int(values[1])

            if current_ply > past_ply:
                game_plies = current_ply
                position["plies"] = game_plies
                positions += 1

            position["ply"] = current_ply

            # set score
            # score = position["score"]

            # 1. initial model - seems to work but dodgy execution
            # use scaled eval 
            # get_sign = lambda s: (s>0) - (s<0)
            # sign = get_sign(score)
            # game_progress = current_ply / game_plies
            # tapered_eval = sign*(game_progress * MAX_EVAL)

            # og_scaled_eval = score

            # mg_known_win = 500
            # mg_scaled_eval = score/mg_known_win * MAX_EVAL

            # eg_scaled_eval = score + tapered_eval

            # game_progress = current_ply / game_plies

            # if game_progress < 0.3:
            #     scaled_eval = int(0.8*og_scaled_eval+0.2*mg_scaled_eval+0.0*eg_scaled_eval)
            # elif game_progress >= 0.3 and game_progress <= 0.6:
            #     scaled_eval = int(0.0*og_scaled_eval+0.5*mg_scaled_eval+0.5*eg_scaled_eval)
            # else:
            #     scaled_eval = int(0.1*og_scaled_eval+0.1*mg_scaled_eval+0.8*eg_scaled_eval)

            # 2. leela style - strangely doesn't work but little data
            # set scaled eval (Q)
            # range of [-1 to 1]
            # q = Q(score, scale)
            # assert q >= -1 and q <= 1

            # scaled_eval = q * MAX_EVAL

            # 3. properly scaled version 1 - confirmed works better than 1
            
            # exponential formula based on
            # game progress and known win cps based on game phase

            # mg_known_win = 1034.96*math.exp(-1.43687*game_progress)
            # assert mg_known_win >= 245 and mg_known_win <= 1035

            # mg_scaled_eval = int(clamp(score/mg_known_win * MAX_EVAL))
            # assert mg_scaled_eval >= -MAX_EVAL and mg_scaled_eval <= MAX_EVAL

            # eg_known_win = 300*math.exp(-1.09861*game_progress)
            # assert eg_known_win >= 85 and eg_known_win <= 350

            # eg_scaled_eval = int(clamp(score/eg_known_win * MAX_EVAL))
            # assert eg_scaled_eval >= -MAX_EVAL and eg_scaled_eval <= MAX_EVAL

            # scaled_eval = int((1-game_progress)*mg_scaled_eval+((game_progress)*eg_scaled_eval))
            # assert scaled_eval >= -MAX_EVAL and scaled_eval <= MAX_EVAL

            # position["score"] = scaled_eval

            position["score"] = 0

            past_ply = current_ply

            # assert position["ply"] != None

        if values[0] == "result":

            result = values[1]
            position["result"] = result
            assert position["result"] != None

            assert position["score"] == 0
            get_sign = lambda s: (s>0) - (s<0)
            sign = get_sign(int(result))
            game_progress = position["ply"] / position["plies"]
            tapered_eval = sign*(game_progress * MAX_EVAL)
            position["score"] = int(tapered_eval)

            # if sign != 0:
            #     assert position["score"] != 0
            # else:
            #     assert position["score"] == 0

        if values[0] == "e":
            positions += 1
            
            if positions % 100000 == 0:
                print(f"parsed positions:", positions)

            output_file.write("fen " + str(position['fen']) + "\n" )
            output_file.write("move " + str(position['move']) + "\n" )
            output_file.write("score " + str(position['score']) + "\n")
            output_file.write("ply " + str(position['ply']) + "\n" )
            output_file.write("result " + str(position['result']) + "\n" )
            output_file.write("e\n")

    plain_file.close()
    output_file.close()

if __name__ == "__main__":
    main()
