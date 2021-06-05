from transitions import Machine

class CaptureSequence(aelf):

    states = ['waiting for signal', 'waiting for delimiter', 'outputting', 'timed out']

    self.current_turn_signal = 0
    self.number_of_turns = 3

    #timeout is seconds from initia
    self.signal_timeout = 5

    self.machine = Machine(model=self, states=CaptureSequence.states, initial='waiting for signal')


   ##commands
  
