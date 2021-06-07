
from time import sleep
from transitions import Machine
from transitions.extensions.states import add_state_features, Tags, Timeout

@add_state_features(Tags, Timeout)
class CustomStateMachine(Machine):
    pass


class CaptureSequence(object):
    states = [{'name': 'wait sequence start'},
              {'name': 'wait signal', 'timeout': 5, 'on_timeout': 'timed_out'},
              {'name': 'sequence complete'}]

    def __init__(self):
        self.current_signal_number = 0
        self.number_of_turns = 3
        self.auto_transitions=False
        #self.waiting_for_signal = False
        self.turn_sequence = [self.number_of_turns]

        self.signal_key = {
            '1*': 'delimiter',
            '2*': 'left',
            '3*': 'right'
        }

        self.machine = CustomStateMachine(model=self, states=CaptureSequence.states, initial='wait sequence start')

        self.machine.add_transition('start', 'wait sequence start', 'wait signal')
        self.machine.add_transition('signal_received', 'wait signal', '=', after=['process_signal'])
        self.machine.add_transition('complete_sequence_received', 'wait signal', 'sequence complete')
        self.machine.add_transition('reset', 'sequence complete', 'wait sequence start')
        self.machine.add_transition('timed_out', '*', 'wait sequence start')


    def proces_signal(self, note):
        signal =  self.signal_key[note]
        if self.waiting_for_signal:
            if signal == 'delimiter':
                #waiting for a signal but still getting delimiter, carry on waiting
                pass
            else:
                #waiting for signal and got a signal, process it and move on
                self.turn_sequence[self.current_signal_number] = signal
                self.current_signal_number += 1
                self.waiting_for_signal = False
                if self.current_signal_number >= self.number_of_turns:
                    #we got all the turns we were expecting
                    self.complete_sequence_received()
        else:
            if signal == 'delimiter':
                #waiting for delimiter and got it, so next we're looking for a signal
                self.waiting_for_signal = True
            else:
                #we got another signal whilst waiting for a delimiter, ignore it
                pass


