import bs4
import sys
import xmltodict
import collections

duration_to_note_attrs = { # we only support up to 32nd notes
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
    63: {'type': '16th'},
    64: {'type': '16th'},

    # dotted 16ths
    96: {'type': '16th', 'dot': ''},

    # 8th triplets
    84: {
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
    190: {'type': 'eighth', 'dot': ''},
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
    252: {'type': 'quarter'},
    254: {'type': 'quarter'},
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

        note.pop('default-x', None)

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

def syncopation_value_beat(beat, method, bin_size, bin_divisions=4, max_bin_granularity=32):
    value = 0
    granularity = max_bin_granularity / bin_divisions

    # Onset Density Measure:
    # - essentially calculates onsets over duration
    # - make sure max_bin_granularity > the max number of possible onsets you might have, otherwise value will be greater than 1
    if method == 'DENSITY':
        total_bin_duration = get_total_bin_duration(beat)
        if total_bin_duration > 0:
            # value = float(len(beat)) / total_bin_duration
            # value = value * bin_size / granularity

            # simplified calculation that accounts for rests
            value = float(len([note for note in beat if 'rest' not in note])) / granularity
    

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
                    cur_value = 3
                else:
                    cur_value = 4

            cur_value = float(cur_value) / 4 # scale it so value < 1
            value += cur_value / len(bin)

            cur_duration += note_duration


    return value

def get_total_bin_duration(bin):
    return reduce(add_duration, [int(note['duration']) for note in bin], 0)

if __name__ == '__main__':
    score_xml_in_path = sys.argv[1]
    score_xml_out_path = sys.argv[2]

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

        # output to validate correct binning
        for bi, bin in enumerate(bins):
            total_duration = get_total_bin_duration(bin)
            sync_density = syncopation_value_beat(bin, 'DENSITY', bin_duration, bin_divisions)
            sync_keith = syncopation_value_beat(bin, 'KEITH', bin_duration, bin_divisions)
            print 'beat {}: {} notes, total_duration={}, sync_density={}, sync_keith={}'.format(bi+1, len(bin), total_duration, sync_density, sync_keith)


        # for bi, bin in enumerate(bins):


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