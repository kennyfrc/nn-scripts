import argparse
import pdb
  
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, required=True)
    parser.add_argument("--ply", type=int, default=0)

    args = parser.parse_args()

    # for avg_after_ply
    after_ply = args.ply
    file = args.file

    plain_file = open(file, "r")

    ply_score = {}
    last_score = None
    plies = 0
    scores = []

    for line in plain_file:
        values = line.split()
        if values[0] == "score":
            last_score = values[1]
            if int(values[1]) < 30000:
                scores.append(int(values[1]))

        if values[0] == "ply":
            assert last_score != None
            ply = values[1]

            if ply in ply_score.keys():
                ply_score[int(ply)].append(abs(int(last_score)))
            else:
                ply_score[int(ply)] = [abs(int(last_score))]
            plies += 1

            if plies % 100000 == 0:
                print(f"positions parsed:", plies)


    sum_evals = 0
    ply_count = 0

    for hsh in sorted(ply_score.items()):
        avg_eval = round(sum(hsh[1]) / len(hsh[1]),2)
        ply = hsh[0]
        print(f"ply: {ply}, avg_eval: {avg_eval} ")

        if ply > after_ply:
            sum_evals += avg_eval
            ply_count += 1

    print(f"file_name: {file}")
    print(f"average eval after ply {after_ply}: {round(sum_evals/ply_count,0)}")
    print(f"max eval after ply {after_ply}:", round(max(scores),2))

    plain_file.close()

if __name__ == "__main__":
    main()
