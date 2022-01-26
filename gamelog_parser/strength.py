from os import stat
import eval7
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# we will train a nn to predict the w% of a hand.
# this is so that we can achieve fast calcuations which mirror the reults
# of a 1000 iter montecarlo estimation (with swaps)

# there will be a nn with different numbers of inputs.
# 2 minimum for the given hand and x for the community cards (0,3,4,5)
# must consider number of possibilities to address the required sample complexity
# ** must be at least the number of params in nn

# preflop: 52!/50!
# flop: 52!/47!
# turn: 52!/46!
# river: 52!/45!


def calc_strength(iters, hole, board, swaps = True):
    """
        adjusted calculation from monte_calo_1
        @param hole: string rep of cards for the given player
        @param board: list of string rep community cards. 
            * Will only calculate EV with given board
        @param swaps: indicates whether traditional or swap texas holdem (10%, 5%)
        @return an estimate of win percentages 

        ** interprets swapped cards as out of deck (in reality they are at bottom of deck) 
        not optimized for swaps = False   
    """
    _FLOP_SWAP = .1 if swaps else 0
    _TURN_SWAP = .05 if swaps else 0 # subject to change

    hole_cards = [eval7.Card(card) for card in hole]
    board_cards = [eval7.Card(card) for card in board]
    deck = eval7.Deck()  # initialize for each version
    for card in hole_cards+board_cards:
            deck.cards.remove(card)
    
    score = 0
    for _ in range(iters):
        deck.shuffle()  # shuffle for each iteration
        random.seed()  # reset seed for each iteration
        
        # indices in terms of hole+deck to allow index if no swap (0,1)
        players = [[0,1], [2, 3]]  # index of player cards
        comm = set()  # index of community cards

        # calculate swaps first so peek, not deal --> shuffle no init
        cind = 4  # current unassigned index
        if len(board) == 0:  # for flop
            [comm.add(x) for x in range(cind, cind+3)]
            cind += 3
            for p in range(2):
                for c in range(2): # two cards
                    if random.random() <= _FLOP_SWAP: 
                        players[p][c] = cind  # should work due to pidgeon hole
                        cind += 1
        if len(board) <= 3: # for turn
            comm.add(cind)
            cind += 1
            for p in range(2):
                for c in range(2): # two cards
                    if random.random() <= _TURN_SWAP: 
                        players[p][c] = cind  # should work due to pidgeon hole
                        cind += 1
        if len(board) <= 4:
            comm.add(cind)

        draw = hole_cards + deck.peek(cind+1) # index = (# cards - 1)
        new_hand = [draw[x] for x in players[0]]  # if no swaps should be hole_cards
        opp_hand = [draw[x] for x in players[1]]
        comm = [draw[x] for x in comm]

        our_hand = new_hand + comm + board_cards
        opp_hand = opp_hand + comm + board_cards

        our_hand_value =  eval7.evaluate(our_hand)
        opp_hand_value = eval7.evaluate(opp_hand)

        if our_hand_value > opp_hand_value:
            score+=2
        elif our_hand_value == opp_hand_value:
            score+=1
        else:
            score+=0
    hand_strength = score/(2*iters)
    return hand_strength

def one_hot(card, eval7 = True):
    """
        @param card, string rep of card
        @return tuple of (one-hot rank, one-hot suit)
        converts a card to its one_hot representation
        ** because in poker, hand strength is based independently
        on a combination of suit and number combinations,
        and since suit and number can be interpretted as being independent events,
        we will limit the representation to [# + suit] in input
    """
    if eval7:
        rank = [0 for _ in range(13)]
        rank[card.rank] = 1  # mask // 13
        suit = [0 for _ in range(4)]
        suit[card.suit] = 1  # mask % 13
        return rank + suit
    else:
        # assures in proper strng form if from gamelog. should be unneccessary
        # assert(re.fullmatch(r'[2-9TJQKA][sdch]', card)) 
        # https://github.com/julianandrews/pyeval7/blob/master/eval7/cards.pyx
        # rank and suit are 0 indexed. mask = 13 * suit + rank
        # rank: 2 ... A, suit: c,d,h,s
        ranks = ('2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A')
        suits = ('c', 'd', 'h', 's')
        cardrank = ranks.index(card[0])
        cardsuit = suits.index(card[1])
        rank = [0 for _ in range(13)]
        rank[cardrank] = 1  # mask // 13
        suit = [0 for _ in range(4)]
        suit[cardsuit] = 1  # mask % 13
        return rank + suit

def samples(_COMM = 0, hands = 100, _ITERS = 1000, swaps = True):
    """
        returns a generator of sample tensors for the given hand type
    """
    to_str = lambda cards: [c.__str__() for c in cards]
    _HOLE = 2
    deck = eval7.Deck()
    X,Y = [], []
    for _ in range(hands):
        cards = deck.peek(_HOLE+_COMM)
        hole_cards = cards[:_HOLE]  # calc_strength takes string
        comm_cards = cards[_HOLE:]
        est = calc_strength(_ITERS, to_str(hole_cards), to_str(comm_cards), swaps = swaps)  # calc_strength takes string
        inputl = [one_hot(card) for card in hole_cards+comm_cards]
        X.append(inputl)
        Y.append(est)
    return X,Y

class Estimator(nn.Module):
    """
        a neural network which predicts the win percentage of a hand
        the first few layers are meant to show the transitory probabilities between betting rounds
        the next layers are used for actually calculating the win percentage given the info
    """
    def __init__(self, comm = 3) -> None:
        super().__init__()
        # two one-hot params per card
        card_params = 13+4
        input_size = (2+comm)*card_params
        calc_layer_size = 24

        # no activation between betting rounds because should just
        # be a uniform distribution ie linear relationship
        self.fc1 = nn.Linear(input_size, calc_layer_size)
        self.fc2 = nn.Linear(calc_layer_size, calc_layer_size)
        self.fc3 = nn.Linear(calc_layer_size, 1)  # output is a #

    def forward(self, x):
        seq = nn.Sequential(  # all hands should get to river
          self.fc1, 
          nn.ReLU(),
          self.fc2,
          nn.ReLU(),
          self.fc3
        )
        return seq(x)

def train(net, params, data):
    lr = params["lr"]
    loss_func = params["loss function"]
    optimizer = params["optimizer"](net.parameters(), lr = lr)
    device = params["device"]
    hands = params["hands"]
    csize = params["csize"]

    X, Y = data
    EPOCHS = 2 # don't want to overfit
    for epoch in range(EPOCHS):
        running_loss = 0.0
        for i in range(hands):  # #cards by 13+4
            x = torch.Tensor(X[i]).to(device)  # convert to tensor
            y = torch.Tensor([Y[i]]).to(device)
            x = x.flatten()
            prediction = net(x)     # input x and predict based on x
            loss = loss_func(prediction, y)     # must be (1. nn output, 2. target)
            optimizer.zero_grad()   # clear gradients for next train
            loss.backward()         # backpropagation, compute gradients
            optimizer.step()        # apply gradients
            running_loss += loss.item()
        print('[%d, %5d] loss: %.3f' %(epoch + 1, csize, running_loss / hands))

def test(net, params): # randomly sampled
    csize = params["csize"]
    hands = params["hands"]
    ITERS = params["ITERS"]
    loss_func = params["loss function"]
    device = params["device"]

    m = 0
    testing_loss = 0.0
    X, Y = samples(_COMM = csize, hands = hands, _ITERS=ITERS)
    for i in range(hands):  # #cards by 13+4
      x = torch.Tensor(X[i]).to(device)  # convert to tensor
      y = torch.Tensor([Y[i]]).to(device)
      x = x.flatten()
      prediction = net(x)     # input x and predict based on x
      loss = loss_func(prediction, y)
      m = max(m, loss.item())
      testing_loss += loss.item()
    print((csize, m, testing_loss / hands))

class StrengthNN:
    def __init__(self) -> None:
        comms = [5,4,3,0]
        self.nets = {}
        for csize in comms:
            state_dict = torch.load('gamelog_parser/strength_inits/est'+str(csize)+".pth", map_location=torch.device('cpu'))
            model = Estimator(csize).to(torch.device('cpu'))
            model.load_state_dict(state_dict)
            self.nets[csize] = model
            model.eval()

    def calc(self, hole, board):
        """
            same format as mc calc_strength
            * swaps is assumed to be true
        """
        csize = len(board)
        input = torch.Tensor([one_hot(card, False) for card in hole+board])  # input is string
        input = input.flatten()
        return self.nets[csize](input)[0]


if __name__ == "__main__":
    deck = eval7.Deck()
    #deck.shuffle()
    hole = [c.__str__() for c in deck.deal(2)]
    board3 = [c.__str__() for c in deck.peek(3)]
    board4 = [c.__str__() for c in deck.peek(4)]
    board5 = [c.__str__() for c in deck.peek(5)]
    strength = StrengthNN()
    print(strength.calc(hole, []), calc_strength(10000, hole, []))
    print(strength.calc(hole, board3), calc_strength(10000, hole, board3))
    print(strength.calc(hole, board4), calc_strength(10000, hole, board4))
    print(strength.calc(hole, board5), calc_strength(10000, hole, board5))
    
        