from matplotlib import pyplot as plt
import eval7
import random
import numpy as np

def mc_accuracy():
    """
        Measures the strength calc variance with mc with a given iter size
        by plotting the moving average through NSAMPLES samples
    """

    NUM_HANDS = 1
    NSAMPLES = 10000
    _FLOP_SWAP = .10
    _TURN_SWAP = 0.05  # should change this param to see var.
    colors = ['ko', 'ro', 'bo', 'go', 'yo', 'mo']
    
    sizes = [20, 50, 100, 250, 1000]  # sizes of moving averages

    deck = eval7.Deck()
    for _ in range(NUM_HANDS):  # number of hands
        deck.shuffle()
        hole_cards = deck.deal(2)

        for csize in {0, 3, 4, 5}:  # symbols ,3,4,5
            deck.shuffle()
            board_cards = deck.deal(csize)
            for swaps in {True}: # False

                # all of the following are in reference to sizes
                histories = [[] for _ in range(len(sizes))]  # historical hand_strength = scores[s]/(2*sizes[s])
                results = [[0]*sizes[s] for s in range(len(sizes))] # results (+0, +1, +2) of sizes[s] simulated games
                scores = [0 for _ in range(len(sizes))]  # current sums of win/tie/losses
                avg_100 = []

                for i in range(NSAMPLES):
                    deck.shuffle()  # shuffle for each iteration
                    random.seed()  # reset seed for each iteration
                    
                    # indices in terms of hole+deck to allow index if no swap (0,1)
                    players = [[0,1], [2, 3]]  # index of player cards
                    comm = set()  # index of community cards

                    # calculate swaps first so peek, not deal --> shuffle no init
                    cind = 4  # current unassigned index
                    if swaps:
                        if csize == 0:  # for flop
                            [comm.add(x) for x in range(cind, cind+3)]
                            cind += 3
                            for p in range(2):
                                for c in range(2): # two cards
                                    if random.random() <= _FLOP_SWAP: 
                                        players[p][c] = cind  # should work due to pidgeon hole
                                        cind += 1
                        if csize <= 3: # for turn
                            comm.add(cind)
                            cind += 1
                            for p in range(2):
                                for c in range(2): # two cards
                                    if random.random() <= _TURN_SWAP: 
                                        players[p][c] = cind  # should work due to pidgeon hole
                                        cind += 1
                        if csize <= 4:
                            comm.add(cind)
                    else:
                        comm_size = 5-len(board_cards)
                        comm = {x for x in range(cind, cind+comm_size)}  # draw next 
                        cind += comm_size

                    draw = hole_cards + deck.peek(cind+1) # index = (# cards - 1)
                    new_hand = [draw[x] for x in players[0]]  # if no swaps should be hole_cards
                    opp_hand = [draw[x] for x in players[1]]
                    comm = [draw[x] for x in comm]

                    our_hand = new_hand + comm + board_cards
                    opp_hand = opp_hand + comm + board_cards

                    our_hand_value =  eval7.evaluate(our_hand)
                    opp_hand_value = eval7.evaluate(opp_hand)

                    for s in range(len(sizes)):
                        scores[s] -= results[s][i%sizes[s]]
                        if our_hand_value > opp_hand_value:
                            results[s][i%sizes[s]] = 2
                            scores[s]+= 2
                        elif our_hand_value == opp_hand_value:
                            results[s][i%sizes[s]] = 1
                            scores[s] += 1
                        else:
                            results[s][i%sizes[s]] = 0
                            scores[s] += 0
                        hand_strength = scores[s]/(2*sizes[s])
                        histories[s].append(hand_strength)
                for s in range(len(histories)):
                    plt.plot(histories[s], colors[s], label = str(sizes[s]) + "samples")
                plt.title(str(csize)+" comm. cards: swaps = " + str(swaps))
                plt.legend()
                plt.show()


if __name__ == '__main__':
    mc_accuracy()
