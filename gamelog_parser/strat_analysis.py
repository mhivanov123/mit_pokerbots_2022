import eval7
import random
from matplotlib.pyplot import draw
import numpy as np
import pandas as pd
from round import Round, parse_gamelog

# make bet analysis' independent of each other
# train model on independent betting round strats and overall strat. 


def data_clean(rounds):
    # get info for each of the betting rounds if applicable
    inputs = { ### TODO fill this out
        "pot": None,
        "pod odds": None,
        "win perc": None,
        "continue cost": None,
        "prev action type": None
    }

    NUM_INPUT = 5
    NUM_BET = 4

    data = np.full((len(rounds), NUM_BET, NUM_INPUT), np.nan)  # filled with np.nan must remove for analysis
    for round in rounds:
        for r in range(round.last_betting_round()):
            pass
            # will consider amount bet as output
            # will interpret ... as input:
            # pot amount, pot odds, W%, continue cost, previous action type




if __name__ == '__main__':
    # run with path arg to gamelog: from gamelog_parser if interactive
    # from folder root if in terminal
    player = 0 # player 0 is challenger (always starts with button)
    log_path = "gamelogs/sadge07.txt"
    rounds = parse_gamelog(log_path)
    pd.DataFrame()