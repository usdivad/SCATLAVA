SCATLAVA: Software for Computer-Assisted Transcription Learning through Algorithmic Variation and Analysis
===================

Transcribing music is an essential part of studying jazz. SCATLAVA is a software framework that analyzes a transcription for difficulty and algorithmically generates variations in an adaptive learning manner in order to aid students in their assimilation and understanding of the musical material and vocabulary, with an emphasis on rhythmic properties to assist jazz drummers and percussionists. The key characteristics examined by the software are onset density, syncopation measure, and limb interdependence (also known as coordination), the last of which introduces the concept of and presents an equation for calculating contextual note interdependence difficulty (CNID).


Usage:

    python scatlava.py tests/notationTest1.xml


Another example with more arguments:

    python scatlava.py tests/notationTest1.xml nout1.xml --target_difficulty=0.8 --gradients=0.4,0.2,0.4 --bin_divisions=2

Full list of parameters (run with `-h` to view):

    SCATLAVA: Software for Computer-Assisted Transcription Learning through
    Algorithmic Variation and Analysis

    positional arguments:
      score_xml_in_path     the original transcription
      score_xml_out_path    the generated modified score

    optional arguments:
      -h, --help            show this help message and exit
      -t TARGET_DIFFICULTY, --target_difficulty TARGET_DIFFICULTY
                            0 to 1, as a ratio of original transcription's
                            difficulty
      -w WEIGHTS, --weights WEIGHTS
                            comma-separated d,s,c. e.g. 0.2,0.1,0.7
      -g GRADIENTS, --gradients GRADIENTS
                            comma-separated d,s,c. e.g. 0.2,0.1,0.7
      -b BIN_DIVISIONS, --bin_divisions BIN_DIVISIONS
                            number of bins to divide a measure into
      -f STOCHASTIC_MODIFIER, --stochastic_modifier STOCHASTIC_MODIFIER
                            0 to 1
      -a, --analysis_only   flag to set analysis mode on or off