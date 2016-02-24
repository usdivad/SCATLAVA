import bs4
import sys
import xmltodict
import collections

# Default duration -> note_attrs for MusicXML construction and analysis
# NOTE: here we only support up to 32nd notes
duration_to_note_attrs = {
    #32nds
    32: {'type': '32nd'},

    # 16th triplets
    42: {
        'type': '16th',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': '16th'
        }
    },
    43: {
        'type': '16th',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': '16th'
        }
    },

    # 16ths
    63: {'type': '16th'}, # rounding
    64: {'type': '16th'},

    # dotted 16ths
    96: {'type': '16th', 'dot': ''},

    # 8th triplets
    84: {  # rounding
        'type': 'eighth',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'eighth'
        }
    },
    85: {
        'type': 'eighth',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'eighth'
        }
    },
    86: {
        'type': 'eighth',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'eighth'
        }
    },

    # 8ths
    126: {'type': 'eighth'}, # for rounding when tripletizing up
    127: {'type': 'eighth'}, # for rounding when tripletizing up
    128: {'type': 'eighth'},
    129: {'type': 'eighth'}, # for rounding when tripletizing up

    # dotted 8ths
    190: {'type': 'eighth', 'dot': ''},  # rounding
    192: {'type': 'eighth', 'dot': ''},

    # quarter triplets
    170: {
        'type': 'quarter',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'quarter'
        }
    },
    171: {
        'type': 'quarter',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'quarter'
        }
    },
    172: {
        'type': 'quarter',
        'time-modification': {
            'actual-notes': 3,
            'normal-notes': 2,
            'normal-type': 'quarter'
        }
    },

    # quarter
    252: {'type': 'quarter'}, # rounding
    254: {'type': 'quarter'}, # rounding
    256: {'type': 'quarter'},

    # dotted quarter
    384: {'type': 'quarter', 'dot': ''},

    # half
    512: {'type': 'half'},

    # dotted half
    768: {'type': 'half', 'dot': ''},

    # whole
    1024: {'type': 'whole'}
}

# Definitions for difficulty values relative to original transcription
# (so D(original_transcription) = 1)
# 


# Calculate overall difficulty of a bin based on d(ensity), k(eith), and c(oordination) as well as corresponding w(eights)
def calculate_difficulty(d, k, c, w={'d': 0.33, 'k': 0.34, 'c': 0.33}):
    return ( (d*w['d']) + (k*w['k']) + (c*w['c']) )


# Augmentation of a note, given several params
def parse_note(note, prev_note, duration_min, duration_left):
    print '{} left'.format(duration_left)
    if is_valid_note(note): # otherwise it's a deleted and we ignore it

        if 'rest' in note:
            return note

        # comparing durations to prev
        duration = int(note['duration'])
        prev_note_dur = int(prev_note['duration'])
        diff = prev_note_dur - duration
        # duration_error_margin = 10
        print '{} - {} = {}'.format(prev_note_dur, duration, diff)

        # comparing note equality from prev
        same_note = False
        if 'unpitched' in note and 'unpitched' in prev_note:
            notename = to_note_name(note)
            prev_notename = to_note_name(prev_note)
            same_note = (notename == prev_notename)

        if diff > 0: #and same_note:
            print 'note of duration {} has been removed'.format(duration)
            # return 'rest'
            return diff

        # testing
        if 'dot' not in note:
            # if 'time-modification' in note:
            #     while duration < duration_min:
            #         print '{} < {}'.format(duration, duration_min)
            #         duration = int(duration * 1.5) # todo: smartly tripletize
            # else:
            #     while duration < duration_min:
            #         print '{} < {}'.format(duration, duration_min)
            #         duration = int(duration * 2)

            while duration < duration_min: #and duration > duration_left:
                print '{} < {}'.format(duration, duration_min)
                if 'time-modification' in duration_to_note_attrs[duration]:
                    duration = int(duration * 1.5)
                else:
                    duration = int(duration * 2)


        note_attrs = duration_to_note_attrs[duration]

        note['duration'] = str(duration)
        note['type'] = note_attrs['type']
        if 'dot' in note_attrs:
            note['dot'] = note_attrs['dot']
        else:
            note.pop('dot', None)
        if 'time-modification' in note_attrs['type']:
            note['time-modification'] = note_attrs['time-modification']
        else:
            note.pop('time-modification', None)

        note.pop('@default-x', None)

        print '{}, {}'.format(note['duration'], note_attrs)
    return note

def tripletize_duration(duration):
    return duration*2/3

def make_data_document(data, label):
    return {'data': {
        label: data
    }}

def debug_unparse(data, label):
    return xmltodict.unparse(make_data_document(data, label))

# def remove_rests(note):
    # return

def to_note_name(note):
    if 'unpitched' not in note:
        return 'B#0'
    unpitched = note['unpitched']
    return '{}{}'.format(unpitched['display-step'], unpitched['display-octave'])

def is_valid_note(note):
    return type(note) is dict or type(note) is collections.OrderedDict

def add_duration(x,y):
    return x+y

def note_to_rest(note):
    rest = {
        'rest': None,
        'duration': note['duration'],
        'type': note['type']
    }
    return rest

# Determine the syncopation value of a beat (bin) via one of several methods
def calculate_value_for_bin(bin, method, bin_size, bin_divisions=4, max_bin_granularity=32):
    value = 0
    granularity = max_bin_granularity / bin_divisions

    # Onset Density Measure:
    # - essentially calculates onsets over duration
    # - make sure max_bin_granularity > the max number of possible onsets you might have, otherwise value will be greater than 1
    if method == 'DENSITY':
        total_bin_duration = get_total_bin_duration(bin)
        if total_bin_duration > 0:
            # value = float(len(beat)) / total_bin_duration
            # value = value * bin_size / granularity

            # simplified calculation that accounts for rests
            value = float(len([note for note in bin if 'rest' not in note])) / granularity
    

    # Keith's Measure:
    # - adapted for bins as it depends on bin_size
    elif method == 'KEITH':
        cur_duration = 0
        value = 0
        for ni, note in enumerate(bin):
            cur_note_on_beat = False
            next_note_on_beat = False
            note_duration = int(note['duration'])
            cur_value = 0

            # is this note on the beat?
            if 'rest' not in note and cur_duration % bin_size == 0:
                cur_note_on_beat = True

            # is the next note on the beat?
            if ni < len(bin) - 1:
                next_note = bin[ni+1]
                if 'rest' not in next_note and cur_duration + note_duration % bin_size == 0:
                    next_note_on_beat = True
            else:
                next_note_on_beat = True


            # score according to keith's measure
            if next_note_on_beat:
                if cur_note_on_beat:
                    cur_value = 0
                else:
                    cur_value = 1
            else:
                if cur_note_on_beat:
                    cur_value = 2
                else:
                    cur_value = 3

            # normalize cur_value
            cur_value = float(cur_value) / 3

            # add to total value
            value += cur_value / len(bin)

            # increment current duration
            cur_duration += note_duration
    
    elif method == 'COORDINATION':
        # print bin[0].keys()
        default_xs = [note['@default-x'] for note in bin]
        print default_xs
        num_notes = len(bin)
        value = 0
        max_simultaneous_limbs = 4 # RH, RF, LH, LF

        for ni, note in enumerate(bin):
            cur_value = 0
            cur_note_name = to_note_name(note)
            next_note_name = cur_note_name
            prev_note_name = cur_note_name

            simultaneous_onsets = len(filter(lambda x: x == note['@default-x'], default_xs))
            # print simultaneous_onsets

            if ni < num_notes - 1:
                next_note = bin[ni+1]
                next_note_name = to_note_name(next_note)
            if ni > 0:
                prev_note = bin[ni-1]
                prev_note_name = to_note_name(prev_note)

            # score according to contextual note interdependence difficulty (CNID) measure
            if cur_note_name != next_note_name:
                cur_value += 1
            if cur_note_name != prev_note_name:
                cur_value += 1
            if prev_note_name != next_note_name and cur_value > 0:
                cur_value += 1
            cur_value += simultaneous_onsets / max_simultaneous_limbs

            # normalize score
            cur_value = float(cur_value) / 4

            # add to total value
            value += cur_value / num_notes


    return value

def get_total_bin_duration(bin):
    return reduce(add_duration, [int(note['duration']) for note in bin], 0)

if __name__ == '__main__':
    score_xml_in_path = sys.argv[1]
    score_xml_out_path = sys.argv[2]
    difficulty_gradient = sys.argv[3]
    minimum_difficulty = sys.argv[4]

    score_xml = ''

    with open(score_xml_in_path, 'r') as f:
        score_xml = f.read()

    score_json = xmltodict.parse(score_xml)
    measures = score_json['score-partwise']['part']['measure'] # a list
    # print measures[3]

    duration_min = 128 # rhythmic granularity of the output score we want
    
    # iterate through measures
    for mi, measure in enumerate(measures):
        notes = measure['note']
        prev_note_dur = 0
        prev_note = {
            'duration': '0',
            'unpitched': {
                'display-step': 'X',
                'display-octave': '-1'
            }
        }
        duration_left = 1024 # default measure length in 4/4
        print 'num notes before: {}'.format(len(notes))

        # another approach: binning
        bin_divisions = 4
        bin_duration = duration_left / bin_divisions
        cur_bin_duration = bin_duration
        bin_i = 0
        bins = [ [] for i in xrange(bin_divisions) ]

        # separate notes into bins by beat
        for ni, note in enumerate(notes):
            if is_valid_note(note) and 'duration' in note:
                cur_bin_duration -= int(note['duration'])
                bins[bin_i].append(note)
            if cur_bin_duration <= 0:
                # print cur_bin_duration
                bin_i = min(bin_i+1, len(bins)-1)

                while cur_bin_duration < 0: # in cases where a note is longer than a bin size
                    bin_i = min(bin_i+1, len(bins)-1)
                    cur_bin_duration += bin_duration

                cur_bin_duration = bin_duration

        # output analysis to validate correct binning
        for bi, bin in enumerate(bins):
            total_duration = get_total_bin_duration(bin)
            bin_density = calculate_value_for_bin(bin, 'DENSITY', bin_duration, bin_divisions)
            bin_keith = calculate_value_for_bin(bin, 'KEITH', bin_duration, bin_divisions)
            bin_coordination = calculate_value_for_bin(bin, 'COORDINATION', bin_duration, bin_divisions)
            difficulty = calculate_difficulty(bin_density, bin_keith, bin_coordination)
            print 'measure {} beat {}: {} notes, total_duration={}, bin_density={}, bin_keith={}, bin_coordination={}, difficulty={}'.format(mi+1, bi+1, len(bin), total_duration, bin_density, bin_keith, bin_coordination, difficulty)


        # create new phrase
        # for bi, bin in enumerate(bins):
        #     bin = adjust_bin()


        # # iterate through notes and adjust durations (or delete note) using parse_note()
        # for ni, note in enumerate(notes):
        #     print 'note {}:'.format(ni)
        #     # note = parse_note(note, prev_note)
        #     note = parse_note(note, {'duration': prev_note_dur}, duration_min, duration_left)

        #     if is_valid_note(note): # otherwise it's a rest and we ignore it
        #         duration = int(note['duration'])
        #         prev_note_dur = duration
        #         duration_left -= duration
        #         prev_note = note
        #     else:
        #         # print note
        #         prev_note_dur = 0
        #         # duration_left -= note
        #         # prev_note['duration'] = 0

        #     notes[ni] = note

        # # notes = filter(remove_rests, notes)
        # notes = [note for note in notes if (is_valid_note(note))]

        # print 'num notes after: {}'.format(len(notes))
        # # print notes

        # measures[mi]['note'] = notes


    print score_json['score-partwise']['part']['measure'][0]['note']


    print debug_unparse(measures[0]['note'][0], 'note')

    with open(score_xml_out_path, 'w') as f:
        xmltodict.unparse(score_json, output=f, pretty=True)

# end