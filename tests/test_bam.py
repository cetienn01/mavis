from structural_variant.constants import *
from structural_variant.bam import read as read_tools
from structural_variant.bam import cigar as cigar_tools
from structural_variant.bam.read import read_pair_strand, read_pair_type, breakpoint_pos
from structural_variant.bam.cache import BamCache
from structural_variant.annotate import load_reference_genome
import unittest
import warnings
from tests import MockRead, MockBamFileHandle
from tests import REFERENCE_GENOME_FILE
from tests import BAM_INPUT

REFERENCE_GENOME = None


def setUpModule():
    warnings.simplefilter("ignore")
    global REFERENCE_GENOME
    REFERENCE_GENOME = load_reference_genome(REFERENCE_GENOME_FILE)
    if 'CTCCAAAGAAATTGTAGTTTTCTTCTGGCTTAGAGGTAGATCATCTTGGT' != REFERENCE_GENOME['fake'].seq[0:50].upper():
        raise AssertionError('fake genome file does not have the expected contents')


class TestBamCache(unittest.TestCase):

    def test___init__(self):
        fh = MockBamFileHandle()
        b = BamCache(fh)
        self.assertEqual(fh, b.fh)

    def test_add_read(self):
        fh = MockBamFileHandle()
        b = BamCache(fh)
        r = MockRead('name')
        b.add_read(r)
        self.assertEqual(1, len(b.cache.values()))
        self.assertEqual(set([r]), b.cache['name'])

    def test_reference_id(self):
        fh = MockBamFileHandle({'1': 0})
        b = BamCache(fh)
        self.assertEqual(0, b.reference_id('1'))
        with self.assertRaises(KeyError):
            b.reference_id('2')

    def test_chr(self):
        fh = MockBamFileHandle({'1': 0})
        b = BamCache(fh)
        r = MockRead('name', 0)
        self.assertEqual('1', b.chr(r))

    def test__generate_fetch_bins_single(self):
        self.assertEqual([(1, 100)], BamCache._generate_fetch_bins(1, 100, 1, 0))

    def test__generate_fetch_bins_multi(self):
        self.assertEqual([(1, 50), (51, 100)], BamCache._generate_fetch_bins(1, 100, 2, 0))

    def test__generate_fetch_bins_multi_gapped(self):
        self.assertEqual([(1, 45), (56, 100)], BamCache._generate_fetch_bins(1, 100, 2, 10))

    def test_fetch_single_read(self):
        b = BamCache(BAM_INPUT)
        s = b.fetch('reference3', 1382,1383,read_limit=1, sample_bins=1)
        self.assertEqual(1,len(s))
        r = list(s)[0]
        self.assertEqual('HISEQX1_11:4:2122:14275:37717:split',r.qname)
        b.close()

    def test_get_mate(self):
        #dependant on fetch working
        b = BamCache(BAM_INPUT)
        s = b.fetch('reference3', 1382,1383,read_limit=1, sample_bins=1)
        self.assertEqual(1,len(s))
        r = list(s)[0]
        self.assertEqual('HISEQX1_11:4:2122:14275:37717:split',r.qname)
        o = b.get_mate(r)
        self.assertEqual(1,len(o))
        self.assertEqual('HISEQX1_11:4:2122:14275:37717:split',o[0].qname)


class TestModule(unittest.TestCase):
    """
    test class for functions in the validate namespace
    that are not associated with a class
    """

    def test_alphabet_matching(self):
        self.assertTrue(DNA_ALPHABET.match('N', 'A'))
        self.assertTrue(DNA_ALPHABET.match('A', 'N'))

    def test_breakpoint_pos(self):
        # ==========+++++++++>
        r = MockRead(reference_start=10, cigar=[(CIGAR.M, 10), (CIGAR.S, 10)])
        self.assertEqual(19, read_tools.breakpoint_pos(r))

        with self.assertRaises(AttributeError):
            breakpoint_pos(r, ORIENT.RIGHT)

        self.assertEqual(19, read_tools.breakpoint_pos(r, ORIENT.LEFT))

        # ++++++++++=========>
        r = MockRead(reference_start=10, cigar=[(CIGAR.S, 10), (CIGAR.M, 10)])
        self.assertEqual(10, read_tools.breakpoint_pos(r))

        with self.assertRaises(AttributeError):
            breakpoint_pos(r, ORIENT.LEFT)

        self.assertEqual(10, read_tools.breakpoint_pos(r, ORIENT.RIGHT))

        with self.assertRaises(AttributeError):
            r = MockRead(reference_start=10, cigar=[(CIGAR.X, 10), (CIGAR.M, 10)])
            read_tools.breakpoint_pos(r, ORIENT.LEFT)


class Testcigar_tools(unittest.TestCase):

    def test_recompute_cigar_mismatch(self):
        r = MockRead(
            reference_start=1456,
            query_sequence='CCCAAACAAC'
                           'TATAAATTTT'
                           'GTAATACCTA'
                           'GAACAATATA'
                           'AATAT',
            cigar=[(CIGAR.M, 45)]
        )
        self.assertEqual([(CIGAR.EQ, 45)], cigar_tools.recompute_cigar_mismatch(r, REFERENCE_GENOME['fake']))

        r = MockRead(
            reference_start=1456,
            query_sequence='TATA'
                           'CCCAAACAAC'
                           'TATAAATTTT'
                           'GTAATACCTA'
                           'GAACAATATA'
                           'AATAT',
            cigar=[(CIGAR.S, 4), (CIGAR.M, 10), (CIGAR.D, 10), (CIGAR.I, 10), (CIGAR.M, 25)]
        )
        self.assertEqual(
            [(CIGAR.S, 4), (CIGAR.EQ, 10), (CIGAR.D, 10), (CIGAR.I, 10), (CIGAR.EQ, 25)],
            cigar_tools.recompute_cigar_mismatch(r, REFERENCE_GENOME['fake'])
        )
        r = MockRead(
            reference_start=1452,
            query_sequence='CAGC'
                           'CCCAAACAAC'
                           'TATAAATTTT'
                           'GTAATACCTA'
                           'GAACAATATA'
                           'AATAT',
            cigar=[(CIGAR.X, 4), (CIGAR.M, 10), (CIGAR.D, 10), (CIGAR.I, 10), (CIGAR.M, 25)]
        )
        self.assertEqual(
            [(CIGAR.X, 4), (CIGAR.EQ, 10), (CIGAR.D, 10), (CIGAR.I, 10), (CIGAR.EQ, 25)],
            cigar_tools.recompute_cigar_mismatch(r, REFERENCE_GENOME['fake'])
        )
        r = MockRead(
            reference_start=1452,
            query_sequence='CAGC'
                           'CCCAAACAAC'
                           'TATAAATTTT'
                           'GTAATACCTA'
                           'GAACAATATA'
                           'AATAT',
            cigar=[(CIGAR.M, 14), (CIGAR.D, 10), (CIGAR.I, 10), (CIGAR.M, 25)]
        )
        self.assertEqual(
            [(CIGAR.X, 4), (CIGAR.EQ, 10), (CIGAR.D, 10), (CIGAR.I, 10), (CIGAR.EQ, 25)],
            cigar_tools.recompute_cigar_mismatch(r, REFERENCE_GENOME['fake'])
        )

    def test_recompute_cigar_mismatch_invalid_cigar_value(self):
        r = MockRead(
            reference_start=1452,
            query_sequence='CAGC'
                           'CCCAAACAAC'
                           'TATAAATTTT'
                           'GTAATACCTA'
                           'GAACAATATA'
                           'AATAT',
            cigar=[(50, 14), (CIGAR.D, 10), (CIGAR.I, 10), (CIGAR.M, 25)]
        )
        with self.assertRaises(NotImplementedError):
            cigar_tools.recompute_cigar_mismatch(r, REFERENCE_GENOME['fake'])

    def test_longest_fuzzy_match(self):
        c = [(CIGAR.S, 10), (CIGAR.EQ, 1), (CIGAR.X, 4), (CIGAR.EQ, 10), (CIGAR.I, 3), (CIGAR.EQ, 5)]
        self.assertEqual(15, cigar_tools.longest_fuzzy_match(c, 1))
        self.assertEqual(10, cigar_tools.longest_fuzzy_match(c, 0))
        self.assertEqual(16, cigar_tools.longest_fuzzy_match(c, 2))
        self.assertEqual(16, cigar_tools.longest_fuzzy_match(c, 4))

    def test_score(self):
        c = [(CIGAR.S, 10), (CIGAR.EQ, 1), (CIGAR.X, 4), (CIGAR.EQ, 10), (CIGAR.I, 3), (CIGAR.EQ, 5)]
        self.assertEqual(22, cigar_tools.score(c))

    def test_score_error(self):
        with self.assertRaises(AssertionError):
            c = [(CIGAR.S, 10), (CIGAR.EQ, 1), (CIGAR.X, 4), (99, 10), (CIGAR.I, 3), (CIGAR.EQ, 5)]
            cigar_tools.score(c)

    def test_match_percent(self):
        c = [(CIGAR.S, 10), (CIGAR.EQ, 1), (CIGAR.X, 4), (CIGAR.EQ, 10), (CIGAR.I, 3), (CIGAR.EQ, 5)]
        self.assertEqual(0.8, cigar_tools.match_percent(c))
        with self.assertRaises(AttributeError):
            cigar_tools.match_percent([(CIGAR.M, 100)])
        with self.assertRaises(AttributeError):
            cigar_tools.match_percent([(CIGAR.S, 100)])

    def test_compute(self):
        # GTGAGTAAATTCAACATCGTTTTT
        # aacttagAATTCAAC---------
        self.assertEqual(
            ([(CIGAR.S, 7), (CIGAR.EQ, 8)], 7),
            cigar_tools.compute('GTGAGTAAATTCAACATCGTTTTT', 'AACTTAGAATTCAAC---------')
        )
        self.assertEqual(
            ([(CIGAR.S, 5), (CIGAR.EQ, 8)], 7),
            cigar_tools.compute('GTGAGTAAATTCAACATCGTTTTT', '--CTTAGAATTCAAC---------')
        )
        self.assertEqual(
            ([(CIGAR.S, 5), (CIGAR.EQ, 8)], 7),
            cigar_tools.compute('GTGAGTAAATTCAACATCGTTTTT', '--CTTAGAATTCAAC---------', False)
        )

        self.assertEqual(
            ([(CIGAR.S, 5), (CIGAR.EQ, 5), (CIGAR.I, 2), (CIGAR.EQ, 1)], 7),
            cigar_tools.compute('GTGAGTAAATTC--CATCGTTTTT', '--CTTAGAATTCAAC---------', False)
        )

        with self.assertRaises(AttributeError):
            cigar_tools.compute('CCTG', 'CCG')

        self.assertEqual(
            ([(CIGAR.EQ, 2), (CIGAR.X, 2)], 0),
            cigar_tools.compute('CCTG', 'CCGT', min_exact_to_stop_softclipping=10)
        )

        self.assertEqual(
            ([(CIGAR.S, 5), (CIGAR.EQ, 8)], 5),
            cigar_tools.compute('--GAGTAAATTCAACATCGTTTTT', '--CTTAGAATTCAAC---------', False)
        )

    def test_convert_for_igv(self):
        c = [(CIGAR.M, 10), (CIGAR.EQ, 10), (CIGAR.X, 10)]
        self.assertEqual([(CIGAR.M, 30)], cigar_tools.convert_for_igv(c))

    def test_extend_softclipping(self):
        self.assertEqual(
            ([(CIGAR.S, 10), (CIGAR.M, 10)], 0),
            cigar_tools.extend_softclipping([(CIGAR.S, 10), (CIGAR.M, 10)], 1)
        )

    def test_extend_softclipping_deletions(self):
        self.assertEqual(
            ([(CIGAR.S, 10), (CIGAR.M, 10)], 1),
            cigar_tools.extend_softclipping([(CIGAR.I, 10), (CIGAR.D, 1), (CIGAR.M, 10)], 1)
        )

    def test_extend_softclipping_mismatch(self):
        with self.assertRaises(AttributeError):
            cigar_tools.extend_softclipping([(CIGAR.X, 10), (CIGAR.M, 20), (CIGAR.X, 10)], 30)

    def test_extend_softclipping_insert(self):
        self.assertEqual(
            ([(CIGAR.S, 10), (CIGAR.S, 2), (CIGAR.S, 5), (CIGAR.M, 10), (CIGAR.S,5)],2),
            cigar_tools.extend_softclipping([(CIGAR.S,10), (CIGAR.M, 2), (CIGAR.I, 5), (CIGAR.M, 10), (CIGAR.I,5)],5)
        )

    def test_alignment_matches(self):
        c = [(CIGAR.M, 10), (CIGAR.EQ, 10), (CIGAR.X, 10)]
        self.assertEqual(30, cigar_tools.alignment_matches(c))

    def test_join(self):
        c = [(CIGAR.M, 10), (CIGAR.X, 10), (CIGAR.X, 10)]
        self.assertEqual([(CIGAR.M, 10), (CIGAR.X, 20)], cigar_tools.join(c))
        k = [(CIGAR.X, 10), (CIGAR.M, 10), (CIGAR.X, 10)]
        self.assertEqual([(CIGAR.M, 10), (CIGAR.X, 30), (CIGAR.M, 10), (CIGAR.X, 10)], cigar_tools.join(c, k))


class TestReadPairStrand(unittest.TestCase):
    def setUp(self):
        self.read1_pos_neg = MockRead(is_reverse=False, is_read1=True, mate_is_reverse=True)
        assert(not self.read1_pos_neg.is_read2)
        self.read1_neg_pos = MockRead(is_reverse=True, is_read1=True, mate_is_reverse=False)
        self.read2_pos_neg = MockRead(is_reverse=False, is_read1=False, mate_is_reverse=True)
        assert(self.read2_pos_neg.is_read2)
        self.read2_neg_pos = MockRead(is_reverse=True, is_read1=False, mate_is_reverse=False)
        self.read1_pos_pos = MockRead(is_reverse=False, is_read1=True, mate_is_reverse=False)
        self.read1_neg_neg = MockRead(is_reverse=True, is_read1=True, mate_is_reverse=True)
        self.read2_pos_pos = MockRead(is_reverse=False, is_read1=False, mate_is_reverse=False)
        self.read2_neg_neg = MockRead(is_reverse=True, is_read1=False, mate_is_reverse=True)
        self.unpaired_pos = MockRead(is_reverse=False, is_paired=False)
        self.unpaired_neg = MockRead(is_reverse=True, is_paired=False)

    def test_read_pair_strand_det_read1(self):
        self.assertEqual(STRAND.POS, read_pair_strand(self.read1_pos_neg, strand_determining_read=1))
        self.assertEqual(STRAND.NEG, read_pair_strand(self.read2_pos_neg, strand_determining_read=1))
        self.assertEqual(STRAND.NEG, read_pair_strand(self.read1_neg_pos, strand_determining_read=1))
        self.assertEqual(STRAND.POS, read_pair_strand(self.read2_neg_pos, strand_determining_read=1))
        self.assertEqual(STRAND.POS, read_pair_strand(self.read1_pos_pos, strand_determining_read=1))
        self.assertEqual(STRAND.POS, read_pair_strand(self.read2_pos_pos, strand_determining_read=1))
        self.assertEqual(STRAND.NEG, read_pair_strand(self.read1_neg_neg, strand_determining_read=1))
        self.assertEqual(STRAND.NEG, read_pair_strand(self.read2_neg_neg, strand_determining_read=1))

    def test_read_pair_strand_det_read2(self):
        self.assertEqual(STRAND.NEG, read_pair_strand(self.read1_pos_neg, strand_determining_read=2))
        self.assertEqual(STRAND.POS, read_pair_strand(self.read2_pos_neg, strand_determining_read=2))
        self.assertEqual(STRAND.POS, read_pair_strand(self.read1_neg_pos, strand_determining_read=2))
        self.assertEqual(STRAND.NEG, read_pair_strand(self.read2_neg_pos, strand_determining_read=2))
        self.assertEqual(STRAND.POS, read_pair_strand(self.read1_pos_pos, strand_determining_read=2))
        self.assertEqual(STRAND.POS, read_pair_strand(self.read2_pos_pos, strand_determining_read=2))
        self.assertEqual(STRAND.NEG, read_pair_strand(self.read1_neg_neg, strand_determining_read=2))
        self.assertEqual(STRAND.NEG, read_pair_strand(self.read2_neg_neg, strand_determining_read=2))

    def test_read_pair_strand_unpaired(self):
        self.assertEqual(STRAND.POS, read_pair_strand(self.unpaired_pos))
        self.assertEqual(STRAND.NEG, read_pair_strand(self.unpaired_neg))


class TestReadPairType(unittest.TestCase):
    def test_read_pair_type_LR(self):
        r = MockRead(
            reference_id=0,
            next_reference_id=0,
            reference_start=1,
            next_reference_start=2,
            is_reverse=False,
            mate_is_reverse=True
        )
        self.assertEqual(READ_PAIR_TYPE.LR, read_pair_type(r))

    def test_read_pair_type_LR_reverse(self):
        r = MockRead(
            reference_id=1,
            next_reference_id=0,
            reference_start=1,
            next_reference_start=2,
            is_reverse=True,
            mate_is_reverse=False
        )
        self.assertEqual(READ_PAIR_TYPE.LR, read_pair_type(r))

    def test_read_pair_type_LL(self):
        r = MockRead(
            reference_id=0,
            next_reference_id=0,
            reference_start=1,
            next_reference_start=2,
            is_reverse=False,
            mate_is_reverse=False
        )
        self.assertEqual(READ_PAIR_TYPE.LL, read_pair_type(r))

    def test_read_pair_type_RR(self):
        r = MockRead(
            reference_id=0,
            next_reference_id=0,
            reference_start=1,
            next_reference_start=2,
            is_reverse=True,
            mate_is_reverse=True
        )
        self.assertEqual(READ_PAIR_TYPE.RR, read_pair_type(r))

    def test_read_pair_type_RL(self):
        r = MockRead(
            reference_id=0,
            next_reference_id=0,
            reference_start=1,
            next_reference_start=2,
            is_reverse=True,
            mate_is_reverse=False
        )
        self.assertEqual(READ_PAIR_TYPE.RL, read_pair_type(r))

    def test_read_pair_type_RL_reverse(self):
        r = MockRead(
            reference_id=1,
            next_reference_id=0,
            reference_start=1,
            next_reference_start=2,
            is_reverse=False,
            mate_is_reverse=True
        )
        self.assertEqual(READ_PAIR_TYPE.RL, read_pair_type(r))