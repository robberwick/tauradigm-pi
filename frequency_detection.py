#!/usr/bin/env python3
"""Show a text-mode spectrogram using live microphone data."""
import argparse
import math
import shutil

import numpy as np
import sounddevice as sd

usage_line = ' press <enter> to quit, +<enter> or -<enter> to change scaling '

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


try:
    columns, _ = shutil.get_terminal_size()
    columns = 25
except AttributeError:
    columns = 25

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
args, remaining = parser.parse_known_args()
if args.list_devices:
    print(sd.query_devices())
    parser.exit(0)
parser = argparse.ArgumentParser(
    description=__doc__ + '\n\nSupported keys:' + usage_line,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[parser])
parser.add_argument(
    '-b', '--block-duration', type=float, metavar='DURATION', default=50,
    help='block size (default %(default)s milliseconds)')
parser.add_argument(
    '-c', '--columns', type=int, default=columns,
    help='width of spectrogram')
parser.add_argument(
    '-d', '--device', type=int_or_str,
    help='input device (numeric ID or substring)')
parser.add_argument(
    '-g', '--gain', type=float, default=10,
    help='initial gain factor (default %(default)s)')
parser.add_argument(
    '-r', '--range', type=float, nargs=2,
    metavar=('LOW', 'HIGH'), default=[50, 600],
    help='frequency range (default %(default)s Hz)')
args = parser.parse_args(remaining)
low, high = args.range
if high <= low:
    parser.error('HIGH must be greater than LOW')

# Create a nice output gradient using ANSI escape sequences.
# Stolen from https://gist.github.com/maurisvh/df919538bcef391bc89f
colors = 30, 34, 35, 91, 93, 97
chars = ' :%#\t#%:'
gradient = []
for bg, fg in zip(colors, colors[1:]):
    for char in chars:
        if char == '\t':
            bg, fg = fg, bg
        else:
            gradient.append('\x1b[{};{}m{}'.format(fg, bg + 10, char))

try:
    samplerate = sd.query_devices(args.device, 'input')['default_samplerate']

    delta_f = (high - low) / (args.columns - 1)
    fftsize = math.ceil(samplerate / delta_f)
    low_bin = math.floor(low / delta_f)
    last_volume =[0]
    last_volume[0] = 0

    def callback(indata, frames, time, status):
        if status:
            text = ' ' + str(status) + ' '
            print('\x1b[34;40m', text.center(args.columns, '#'),'\x1b[0m', sep=' ')
        if any(indata):
            magnitude = np.abs(np.fft.rfft(indata[:, 0], n=fftsize))
            magnitude *= args.gain / fftsize
            max_component = np.amax(magnitude)
            dominant_frequency = np.where(magnitude == np.amax(magnitude))[0][0]
            if (max_component > 0.2) and (max_component > last_volume[0]):
                components = np.where(magnitude>0.2)
                first_frequency = np.argmax(magnitude > max_component/4)
                print("new")
#                print(first_frequency)
#                print(components)
                df = dominant_frequency
#                print(df)
                one = 35*magnitude[6] + magnitude[20] + magnitude[45] + magnitude[46] + 1.5*magnitude[47]
                two = 15*magnitude[8] + 6*magnitude[9] + magnitude[23] + magnitude[54]
                three = 25*magnitude[11] + 1.5*magnitude[25] + 2*magnitude[26] + 2*magnitude[62] + magnitude[63] + magnitude[99] + magnitude[100]
                four = 7*magnitude[13] + 1.2*magnitude[27] + magnitude[67] + magnitude[107]
                five = 15*magnitude[16] + magnitude[30] + 1.5*magnitude[45]
                six = 10*magnitude[19] + 2*magnitude[34] + magnitude[87]
                seven = 8*magnitude[7] + 2.5*magnitude[22] + magnitude[36] + magnitude[37] + magnitude[47]
                onestar = 5*magnitude[25] + 9*magnitude[26] + 2*magnitude[40] + magnitude[41] + 2*magnitude[55] + magnitude[56] + magnitude[92]
                twostar = 5*magnitude[31] + 5*magnitude[32] + 1.5*magnitude[46]
                threestar = 4*magnitude[37] + 4*magnitude[38] + magnitude[52]
                fourstar = magnitude[25] + 8*magnitude[40] + magnitude[54] + magnitude[55] + 10*magnitude[69]
                fivestar = magnitude[45] + magnitude[46] + 1.5*magnitude[47] + 12*magnitude[61]
                max_value=max(one, two, three, four, five, six, seven, onestar, twostar, threestar, fourstar, fivestar)
                print("1") if one == max_value else ""
                print("2") if two == max_value else ""
                print("3") if three == max_value else ""
                print("4") if four == max_value else ""
                print("5") if five == max_value else ""
                print("6") if six == max_value else ""
                print("7") if seven == max_value else ""
                print("1*") if onestar == max_value else ""
                print("2*") if twostar == max_value else ""
                print("3*") if threestar == max_value else ""
                print("4*") if fourstar == max_value else ""
                print("5*") if fivestar == max_value else ""
#            line = (gradient[int(np.clip(x, 0, 1) * (len(gradient) - 1))]
#                    for x in magnitude[low_bin:low_bin + args.columns])
#            print(*line, sep=' ', end='\x1b[0m\n')
            last_volume[0] = max_component
        else:
            print('no input')

    with sd.InputStream(device=args.device, channels=1, callback=callback,
                        blocksize=int(samplerate * args.block_duration / 1000),
                        samplerate=samplerate):
        while True:
            response = input()
            if response in ('', 'q', 'Q'):
                break
            for ch in response:
                if ch == '+':
                    args.gain *= 2
                elif ch == '-':
                    args.gain /= 2
                else:
                    print('\x1b[31;40m', usage_line.center(args.columns, '#'),'\x1b[0m', sep=' ')
                    break
except KeyboardInterrupt:
    parser.exit('Interrupted by user')
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))
