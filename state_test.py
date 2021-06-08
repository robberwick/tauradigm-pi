from time import sleep
from turn_signal_states import CaptureSequence

#very basic test script to check state machine transitions and handles signals as it should

sequence = CaptureSequence()
print(sequence.state)

sequence.start()
print(sequence.state)

sleep(1)
print("sending signal 1*")
sequence.signal_received("1*")
print(sequence.turn_sequence)
print(sequence.current_signal_number)
print(sequence.state)
sleep(1)
print("sending signal 2*")
sequence.signal_received("2*")
print(sequence.current_signal_number)
print(sequence.turn_sequence)

sleep(1)
print("sending signal 1*")
sequence.signal_received("1*")
print(sequence.current_signal_number)
print(sequence.turn_sequence)

sleep(1)
print("sending signal 2*")
sequence.signal_received("2*")
print(sequence.current_signal_number)
print(sequence.turn_sequence)
sleep(1)
print("sending signal 1*")
sequence.signal_received("1*")
print(sequence.current_signal_number)
print(sequence.turn_sequence)
sleep(1)
print("sending signal 3*")
sequence.signal_received("3*")
print(sequence.current_signal_number)
print(sequence.turn_sequence)

#test timeout
print(sequence.state)
sleep(6)
print(sequence.state)

