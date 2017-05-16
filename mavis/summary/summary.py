from ..constants import COLUMNS, STRAND, CALL_METHOD
from ..breakpoint import Breakpoint, BreakpointPair


def alphanumeric_choice(bpp1, bpp2):
    """
    Args:
        bpp1 (BreakpointPair)
        bpp2 (BreakpointPair)

    returns the one with transcript with alphanumeric priority, with transcript1 chosen for ties
    """
    chosen1 = sorted([bpp1.data[COLUMNS.transcript1], bpp2.data[COLUMNS.transcript1]])[0]
    chosen2 = sorted([bpp1.data[COLUMNS.transcript2], bpp2.data[COLUMNS.transcript2]])[0]
    if bpp1.data[COLUMNS.transcript1] == chosen1 and \
            bpp1.data[COLUMNS.transcript1] != bpp2.data[COLUMNS.transcript1]:
        return bpp1
    elif bpp1.data[COLUMNS.transcript2] == chosen2:
        return bpp1
    else:
        return bpp2


def compare_bpp_annotations(bpp1, bpp2, best_transcripts):
    """
    Args:
        bpp1 (BreakPointPair):
        bpp2 (BreakpointPair):
        best_transcripts (dict):
    """
    # By priority
    # Case 1 an event has 2 genes and transcripts and a fusion cdna (orf)
    if bpp1.data[COLUMNS.fusion_cdna_coding_start] or bpp2.data[COLUMNS.fusion_cdna_coding_start]:
        # take the one with the longest cdna length
        if bpp1.data[COLUMNS.fusion_cdna_coding_start] is None:
            return bpp2
        elif bpp2.data[COLUMNS.fusion_cdna_coding_start] is None:
            return bpp1
        else:
            bpp1_cdna_len = int(bpp1.data[COLUMNS.fusion_cdna_coding_end]) - \
                int(bpp1.data[COLUMNS.fusion_cdna_coding_start])
            bpp2_cdna_len = int(bpp2.data[COLUMNS.fusion_cdna_coding_end]) - \
                int(bpp2.data[COLUMNS.fusion_cdna_coding_start])
            return bpp1 if bpp1_cdna_len >= bpp2_cdna_len else bpp2

    # Case 2 an event has 2 genes and transcripts
    elif bpp1.data[COLUMNS.gene1] and bpp1.data[COLUMNS.gene2] or bpp2.data[COLUMNS.gene1] and bpp2.data[COLUMNS.gene2]:
        # take the one with transcripts that are in best transcript, or the highest alphanumeric name
        if bpp1.data[COLUMNS.gene1] is None or bpp1.data[COLUMNS.gene2] is None:
            return bpp2
        elif bpp2.data[COLUMNS.gene1] is None or bpp2.data[COLUMNS.gene2] is None:
            return bpp1
        else:
            bpp1_t1, bpp1_t2 = (bpp1.data[COLUMNS.transcript1], bpp1.data[COLUMNS.transcript2])
            bpp2_t1, bpp2_t2 = (bpp2.data[COLUMNS.transcript1], bpp2.data[COLUMNS.transcript2])
            # both in best transcripts
            if bpp1_t1 in best_transcripts and bpp1_t2 in best_transcripts and bpp2_t1 in best_transcripts \
                    and bpp2_t2 in best_transcripts:
                return alphanumeric_choice(bpp1, bpp2)
            elif bpp1_t1 in best_transcripts and bpp1_t2 in best_transcripts:
                return bpp1
            elif bpp2_t1 in best_transcripts and bpp2_t2 in best_transcripts:
                return bpp2
            elif bpp1_t1 in best_transcripts or bpp1_t2 in best_transcripts:
                return bpp1
            elif bpp2_t1 in best_transcripts or bpp2_t2 in best_transcripts:
                return bpp2
            else:
                return alphanumeric_choice(bpp1, bpp2)

    # Case 3 an event has 1 gene and transcript
    elif bpp1.data[COLUMNS.gene1] or bpp1.data[COLUMNS.gene2] or bpp2.data[COLUMNS.gene1] or bpp2.data[COLUMNS.gene2]:
        # take the one with transcripts that are in best transcript, or the highest alphanumeric name
        if bpp1.data[COLUMNS.gene1] is None and bpp1.data[COLUMNS.gene2] is None:
            return bpp2
        elif bpp2.data[COLUMNS.gene1] is None and bpp2.data[COLUMNS.gene2] is None:
            return bpp1
        else:
            bpp1_t1, bpp1_t2 = (bpp1.data[COLUMNS.transcript1], bpp1.data[COLUMNS.transcript2])
            bpp2_t1, bpp2_t2 = (bpp2.data[COLUMNS.transcript1], bpp2.data[COLUMNS.transcript2])

            if bpp1_t1 in best_transcripts or bpp1_t2 in best_transcripts:
                return bpp1
            elif bpp2_t1 in best_transcripts or bpp2_t2 in best_transcripts:
                return bpp2
            else:
                return alphanumeric_choice(bpp1, bpp2)

    # Case 4 both have no genes present - will keep the positive strand event
    else:
        if bpp1.break1.strand == STRAND.POS:
            return bpp1
        else:
            return bpp2


def combine_evidence(bpp_to_keep, bpp_to_add):
    # combine the untemplated sequences
    if bpp_to_add.data[COLUMNS.untemplated_seq] is not None:
        bpp_to_keep.data[COLUMNS.untemplated_seq] = bpp_to_add.data[COLUMNS.untemplated_seq] if \
            bpp_to_keep.data[COLUMNS.untemplated_seq] is None else \
            ';'.join(sorted(list(set(bpp_to_add.data[COLUMNS.untemplated_seq],
                                     bpp_to_keep.data[COLUMNS.untemplated_seq]))))

    # combine the contig sequences
    if bpp_to_add.data[COLUMNS.contig_seq] is not None:
        bpp_to_keep.data[COLUMNS.contig_seq] = bpp_to_add.data[COLUMNS.contig_seq] if \
            bpp_to_keep.data[COLUMNS.contig_seq] is None else \
            ';'.join(sorted(list(set(bpp_to_add.data[COLUMNS.contig_seq],
                                     bpp_to_keep.data[COLUMNS.contig_seq]))))

    return bpp_to_keep


def group_events(bpp1, bpp2):
    # todo: decide whether to also aggregate the contig, untemplated and annotation information?
    # take the outer regions of the breakpoints
    new_bpp = BreakpointPair(
        Breakpoint(bpp1.break1.chr,
                   min(bpp1.break1.start, bpp2.break1.start),
                   max(bpp1.break1.end, bpp2.break1.end),
                   orient=bpp1.break1.orient,
                   strand=bpp1.break1.strand),
        Breakpoint(bpp1.break2.chr,
                   min(bpp1.break2.start, bpp2.break2.start),
                   max(bpp1.break2.end, bpp2.break2.end),
                   orient=bpp1.break2.orient,
                   strand=bpp1.break2.strand),
        opposing_strands=bpp1.opposing_strands,
        stranded=bpp1.stranded)

    # remove any attributes that aren't the same in both breakpoints
    if bpp1.data.keys() != bpp2.data.keys():
        raise NotImplementedError("Could not group events that have different data attributes")
    for i in bpp1.data.keys():
        if bpp1.data[i] != bpp2.data[i]:
            # new_bpp.data[i] = None
            new_bpp.data[i] = ";".join([str(bpp1.data[i]), str(bpp2.data[i])])
        else:
            new_bpp.data[i] = bpp1.data[i]
    if bpp1.untemplated_seq == bpp2.untemplated_seq:
        new_bpp.untemplated_seq = bpp1.untemplated_seq

    return new_bpp


def annotate_aliases(bpp, reference_transcripts):
    # Should add the getting the alias to annotate instead of here?
    if bpp.data[COLUMNS.transcript1] in reference_transcripts:
        bpp.data[COLUMNS.gene1_aliases] = ",".join(reference_transcripts[bpp.data[COLUMNS.transcript1]].gene.aliases)
    if bpp.data[COLUMNS.transcript2] in reference_transcripts:
        bpp.data[COLUMNS.gene2_aliases] = ",".join(reference_transcripts[bpp.data[COLUMNS.transcript2]].gene.aliases)
    return(bpp)


def filter_by_evidence(
    bpps, 
    filter_min_remapped_reads=5, 
    filter_min_spanning_reads=5, 
    filter_min_flanking_reads=5, 
    filter_min_flanking_only_reads=10,
    filter_min_split_reads=5,
    filter_min_linking_split_reads=1
):
    filtered = []
    for bpp in bpps:
        if bpp.break1_call_method == CALL_METHOD.CONTIG and bpp.break2_call_method == CALL_METHOD.CONTIG:
            # inherently the breakpoints have been linked
            if bpp.contig_remapped_reads < filter_min_remapped_reads:
                continue
        elif bpp.break1_call_method == CALL_METHOD.SPAN and bpp.break2_call_method == CALL_METHOD.SPAN:
            if bpp.spanning_reads < filter_min_spanning_reads:
                continue
        elif bpp.break1_call_method == CALL_METHOD.SPLIT and bpp.break2_call_method == CALL_METHOD.SPLIT:
            if any([
                bpp.break1_split_reads < filter_min_split_reads,
                bpp.break2_split_reads < filter_min_split_reads,
                bpp.break2_split_reads_forced + bpp.break1_split_reads_forced < filter_min_linking_split_reads
            ]):
                continue
        elif bpp.break1_call_method == CALL_METHOD.SPLIT and bpp.break2_call_method == CALL_METHOD.FLANK:
            if bpp.break1_split_reads < filter_min_split_reads or bpp.flanking_pairs < filter_min_flanking_reads:
                continue
        elif bpp.break1_call_method == CALL_METHOD.FLANK and bpp.break2_call_method == CALL_METHOD.SPLIT:
            if bpp.break1_split_reads < filter_min_split_reads or bpp.flanking_pairs < filter_min_flanking_reads:
                continue
        elif bpp.break1_call_method == CALL_METHOD.FLANK and bpp.break2_call_method == CALL_METHOD.FLANK:
            if bpp.flanking_pairs < filter_min_flanking_only_reads:
                continue
        else:
            raise AssertionError('unexpected value for break1_call_method or break2_call_method: {}, {}'.format(
                bpp.break1_call_method, bpp.break2_call_method))
        filtered.append(bpp)
    return bpp
