import unittest

from mavis.constants import ORIENT, STRAND, SVTYPE
from mavis.tools import _convert_tool_row, SUPPORTED_TOOL, _parse_transabyss, _parse_chimerascan, _parse_bnd_alt

from .mock import Mock


class TestDelly(unittest.TestCase):

    def test_convert_insertion(self):
        row = Mock(
            chrom='1', pos=247760043, id='1DEL00000330',
            info={'SVTYPE': 'INS', 'CT': 'NtoN', 'CHR2': '1', 'CIEND': [-10, 10], 'CIPOS': [-10, 10]},
            stop=247760044
        )
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.DELLY, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('1', bpp.break1.chr)
        self.assertEqual(247760043 - 10, bpp.break1.start)
        self.assertEqual(247760043 + 10, bpp.break1.end)
        self.assertEqual(ORIENT.LEFT, bpp.break1.orient)
        self.assertEqual(STRAND.NS, bpp.break1.strand)
        self.assertEqual(247760044 - 10, bpp.break2.start)
        self.assertEqual(247760044 + 10, bpp.break2.end)
        self.assertEqual(ORIENT.RIGHT, bpp.break2.orient)
        self.assertEqual(STRAND.NS, bpp.break2.strand)
        self.assertEqual('1', bpp.break2.chr)
        self.assertEqual(SVTYPE.INS, bpp.event_type)
        self.assertEqual('', bpp.untemplated_seq)

        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.DELLY, False, assume_no_untemplated=False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual(None, bpp.untemplated_seq)
        self.assertNotEqual('', bpp.untemplated_seq)

    def test_convert_convert_translocation(self):
        row = Mock(
            chrom='7', pos=21673582, id='TRA00016056',
            info={
                'SVTYPE': 'TRA',
                'CT': '5to5',
                'CIEND': [-700, 700],
                'CIPOS': [-700, 700],
                'CHR2': '2'
            },
            stop=58921502
        )
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.DELLY, False)
        for b in bpp_list:
            print(b)
        self.assertEqual(1, len(bpp_list))
        row.info['CT'] = 'NtoN'
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.DELLY, False)
        for b in bpp_list:
            print(b)
        self.assertEqual(4, len(bpp_list))


class TestTransAbyss(unittest.TestCase):

    def test_convert_stranded_indel_insertion(self):
        row = {
            'chr': '1', 'chr_start': '10015', 'chr_end': '10015', 'ctg_strand': '-', 'type': 'ins', 'alt': 'aat', 'id': 1
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.TA, True)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('1', bpp.break1.chr)
        self.assertEqual('1', bpp.break2.chr)
        self.assertEqual(10015, bpp.break1.start)
        self.assertEqual(10016, bpp.break2.start)
        self.assertEqual(SVTYPE.INS, bpp.event_type)
        self.assertEqual(False, bpp.opposing_strands)
        self.assertEqual(STRAND.POS, bpp.break1.strand)
        self.assertEqual(STRAND.POS, bpp.break2.strand)
        self.assertEqual(True, bpp.stranded)
        self.assertEqual('AAT', bpp.untemplated_seq)

    def test_convert_indel_deletion(self):
        row = {
            'id': '1177',
            'type': 'del',
            'chr': 'X',
            'chr_start': '153523769',
            'chr_end': '153523790',
            'alt': 'na',
            'ctg_strand': '+',
            '_index': 9
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.TA, True)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('', bpp.untemplated_seq)

    def test_convert_indel_unstranded_insertion(self):
        row = {
            'id': '1',
            'type': 'ins',
            'chr': '1',
            'chr_start': '8877520',
            'chr_end': '8877520',
            'alt': 'tt',
            'ctg_strand': '+',
            '_index': 1
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.TA, False)
        print([str(b) for b in bpp_list])
        self.assertEqual(1, len(bpp_list))

        bpp = bpp_list[0]
        self.assertEqual(SVTYPE.INS, bpp.event_type)
        self.assertEqual(STRAND.NS, bpp.break1.strand)
        self.assertEqual(STRAND.NS, bpp.break2.strand)
        self.assertEqual(False, bpp.stranded)
        self.assertEqual(False, bpp.opposing_strands)
        self.assertEqual('TT', bpp.untemplated_seq)

    def test_convert_indel_duplication(self):
        row = {
            'id': '1185',
            'type': 'dup',
            'chr': 'GL000211.1',
            'chr_start': '108677',
            'chr_end': '108683',
            'alt': 'aaaaaaa',
            'ctg_strand': '+',
            '_index': 15
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.TA, False)
        print([str(b) for b in bpp_list])
        self.assertEqual(1, len(bpp_list))

        bpp = bpp_list[0]
        self.assertEqual(SVTYPE.DUP, bpp.event_type)
        self.assertEqual(STRAND.NS, bpp.break1.strand)
        self.assertEqual(STRAND.NS, bpp.break2.strand)
        self.assertEqual(False, bpp.stranded)
        self.assertEqual(False, bpp.opposing_strands)
        self.assertEqual('', bpp.untemplated_seq)

    def test_convert_translocation(self):
        raise unittest.SkipTest('TODO')

    def test_convert_stranded_translocation(self):
        row = {
            'strands': '+,-',
            'rearrangement': 'translocation',
            'breakpoint': '17:16342728|17:39766281',
            'orientations': 'L,L',
            'type': 'sense_fusion',
            '_index': 5261,
            'id': 1
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.TA, True)
        self.assertEqual(1, len(bpp_list))

    def test_parse_stranded_translocation(self):
        row = {
            'strands': '+,-',
            'rearrangement': 'translocation',
            'breakpoint': '17:16342728|17:39766281',
            'orientations': 'L,L',
            'type': 'sense_fusion',
            '_index': 5261,
            'id': 1
        }
        std = _parse_transabyss(row)
        print(std)
        self.assertTrue('event_type' not in std)


class TestManta(unittest.TestCase):

    def test_convert_deletion(self):
        row = Mock(
            chrom='21', pos=9412306, id='MantaDEL:20644:0:2:0:0:0',
            info={
                'SVTYPE': 'DEL',
                'CIPOS': [0, 4],
                'CIEND': [0, 4]
            }, stop=9412400
        )
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.MANTA, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('21', bpp.break1.chr)
        self.assertEqual(9412306, bpp.break1.start)
        self.assertEqual(9412310, bpp.break1.end)
        self.assertEqual(9412400, bpp.break2.start)
        self.assertEqual(9412404, bpp.break2.end)
        self.assertEqual('21', bpp.break2.chr)
        print(bpp, bpp.tracking_id)
        self.assertEqual('manta-MantaDEL:20644:0:2:0:0:0', bpp.tracking_id)

    def test_convert_duplication(self):
        row = Mock(
            chrom='1', pos=224646602, id='MantaDUP:TANDEM:22477:0:1:0:9:0',
            info={
                'SVTYPE': 'DUP',
                'SVINSSEQ': 'CAAAACTTACTATAGCAGTTCTGTGAGCTGCTCTAGC'
            }, stop=224800120
        )
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.MANTA, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('1', bpp.break1.chr)
        self.assertEqual('1', bpp.break2.chr)
        self.assertEqual('manta-MantaDUP:TANDEM:22477:0:1:0:9:0', bpp.tracking_id)


class TestDefuse(unittest.TestCase):

    def test_convert_inverted_translocation(self):
        row = {
            'gene_chromosome1': 'X',
            'gene_chromosome2': '3',
            'genomic_break_pos1': '153063989',
            'genomic_break_pos2': '50294136',
            'genomic_strand1': '+',
            'genomic_strand2': '-',
            'cluster_id': 1
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.DEFUSE, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('3', bpp.break1.chr)
        self.assertEqual('X', bpp.break2.chr)
        self.assertEqual(50294136, bpp.break1.start)
        self.assertEqual(153063989, bpp.break2.start)
        self.assertEqual(None, bpp.event_type)
        self.assertEqual(False, bpp.opposing_strands)
        self.assertEqual(ORIENT.RIGHT, bpp.break1.orient)
        self.assertEqual(ORIENT.LEFT, bpp.break2.orient)
        self.assertEqual(False, bpp.stranded)
        self.assertEqual('defuse-1', bpp.tracking_id)

    def test_convert_translocation(self):
        row = {
            'gene_chromosome1': 'X',
            'gene_chromosome2': '3',
            'genomic_break_pos1': '153063989',
            'genomic_break_pos2': '50294136',
            'genomic_strand1': '+',
            'genomic_strand2': '+',
            'cluster_id': 1
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.DEFUSE, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('3', bpp.break1.chr)
        self.assertEqual('X', bpp.break2.chr)
        self.assertEqual(50294136, bpp.break1.start)
        self.assertEqual(153063989, bpp.break2.start)
        self.assertEqual(None, bpp.event_type)
        self.assertEqual(True, bpp.opposing_strands)
        self.assertEqual(ORIENT.LEFT, bpp.break1.orient)
        self.assertEqual(ORIENT.LEFT, bpp.break2.orient)
        self.assertEqual(False, bpp.stranded)
        self.assertEqual('defuse-1', bpp.tracking_id)

    def test_convert_indel(self):
        row = {
            'gene_chromosome1': '1',
            'gene_chromosome2': '1',
            'genomic_break_pos1': '151732089',
            'genomic_break_pos2': '1663681',
            'genomic_strand1': '-',
            'genomic_strand2': '+',
            'cluster_id': 1
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.DEFUSE, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('1', bpp.break1.chr)
        self.assertEqual('1', bpp.break2.chr)
        self.assertEqual(1663681, bpp.break1.start)
        self.assertEqual(151732089, bpp.break2.start)
        self.assertEqual(None, bpp.event_type)
        self.assertEqual(False, bpp.opposing_strands)
        self.assertEqual(ORIENT.LEFT, bpp.break1.orient)
        self.assertEqual(ORIENT.RIGHT, bpp.break2.orient)
        self.assertEqual(False, bpp.stranded)
        self.assertEqual('defuse-1', bpp.tracking_id)

    def test_convert_inversion(self):
        row = {
            'gene_chromosome1': '1',
            'gene_chromosome2': '1',
            'genomic_break_pos1': '235294748',
            'genomic_break_pos2': '144898348',
            'genomic_strand1': '+',
            'genomic_strand2': '+',
            'cluster_id': 1
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.DEFUSE, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('1', bpp.break1.chr)
        self.assertEqual('1', bpp.break2.chr)
        self.assertEqual(144898348, bpp.break1.start)
        self.assertEqual(235294748, bpp.break2.start)
        self.assertEqual(None, bpp.event_type)
        self.assertEqual(True, bpp.opposing_strands)
        self.assertEqual(ORIENT.LEFT, bpp.break1.orient)
        self.assertEqual(ORIENT.LEFT, bpp.break2.orient)
        self.assertEqual(False, bpp.stranded)
        self.assertEqual('defuse-1', bpp.tracking_id)


class TestChimerascan(unittest.TestCase):

    def test_convert_pos_pos(self):
        row = {
            'chrom5p': 'chr3',
            'start5p': '48599150',
            'end5p': '48601200',
            'chrom3p': 'chr3',
            'start3p': '49555116',
            'end3p': '49587666',
            'strand5p': '+',
            'strand3p': '+',
            'chimera_cluster_id': 'CLUSTER30'
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.CHIMERASCAN, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('3', bpp.break1.chr)
        self.assertEqual('3', bpp.break2.chr)
        print(bpp)
        self.assertEqual(int(row['end5p']), bpp.break1.start)
        self.assertEqual(int(row['start3p']), bpp.break2.start)
        self.assertEqual(False, bpp.opposing_strands)
        self.assertEqual(ORIENT.LEFT, bpp.break1.orient)
        self.assertEqual(ORIENT.RIGHT, bpp.break2.orient)
        self.assertEqual(False, bpp.stranded)

    def test_convert_pos_neg(self):
        row = {
            'chrom5p': 'chr3',
            'start5p': '48599150',
            'end5p': '48601200',
            'chrom3p': 'chr3',
            'start3p': '49555116',
            'end3p': '49587666',
            'strand5p': '+',
            'strand3p': '-',
            'chimera_cluster_id': 'CLUSTER30'
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.CHIMERASCAN, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('3', bpp.break1.chr)
        self.assertEqual('3', bpp.break2.chr)
        print(bpp)
        self.assertEqual(int(row['end5p']), bpp.break1.start)
        self.assertEqual(int(row['end3p']), bpp.break2.start)
        self.assertEqual(True, bpp.opposing_strands)
        self.assertEqual(ORIENT.LEFT, bpp.break1.orient)
        self.assertEqual(ORIENT.LEFT, bpp.break2.orient)
        self.assertEqual(False, bpp.stranded)

    def test_convert_neg_pos(self):
        row = {
            'chrom5p': 'chr3',
            'start5p': '48599150',
            'end5p': '48601200',
            'chrom3p': 'chr3',
            'start3p': '49555116',
            'end3p': '49587666',
            'strand5p': '-',
            'strand3p': '+',
            'chimera_cluster_id': 'CLUSTER30'
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.CHIMERASCAN, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('3', bpp.break1.chr)
        self.assertEqual('3', bpp.break2.chr)
        print(bpp)
        self.assertEqual(int(row['start5p']), bpp.break1.start)
        self.assertEqual(int(row['start3p']), bpp.break2.start)
        self.assertEqual(True, bpp.opposing_strands)
        self.assertEqual(ORIENT.RIGHT, bpp.break1.orient)
        self.assertEqual(ORIENT.RIGHT, bpp.break2.orient)
        self.assertEqual(False, bpp.stranded)

    def test_convert_neg_neg(self):
        row = {
            'chrom5p': 'chr3',
            'start5p': '48599150',
            'end5p': '48601200',
            'chrom3p': 'chr3',
            'start3p': '49555116',
            'end3p': '49587666',
            'strand5p': '-',
            'strand3p': '-',
            'chimera_cluster_id': 'CLUSTER30'
        }
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.CHIMERASCAN, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('3', bpp.break1.chr)
        self.assertEqual('3', bpp.break2.chr)
        print(bpp)
        self.assertEqual(int(row['start5p']), bpp.break1.start)
        self.assertEqual(int(row['end3p']), bpp.break2.start)
        self.assertEqual(False, bpp.opposing_strands)
        self.assertEqual(ORIENT.RIGHT, bpp.break1.orient)
        self.assertEqual(ORIENT.LEFT, bpp.break2.orient)
        self.assertEqual(False, bpp.stranded)


class TestPindel(unittest.TestCase):

    def test_convert_deletion(self):
        row = Mock(
            chrom='21', pos=9412306,
            info={
                'SVTYPE': 'DEL'
            },
            stop=9412400, id=None
        )
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.PINDEL, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('21', bpp.break1.chr)
        self.assertEqual('21', bpp.break2.chr)
        self.assertEqual(SVTYPE.DEL, bpp.event_type)
        self.assertEqual(row.pos, bpp.break1.start)
        self.assertEqual(row.pos, bpp.break1.end)
        self.assertEqual(row.stop, bpp.break2.start)
        self.assertEqual(row.stop, bpp.break2.end)
        self.assertEqual(ORIENT.LEFT, bpp.break1.orient)
        self.assertEqual(STRAND.NS, bpp.break1.strand)
        self.assertEqual(ORIENT.RIGHT, bpp.break2.orient)
        self.assertEqual(STRAND.NS, bpp.break2.strand)
        self.assertEqual(False, bpp.stranded)
        self.assertEqual(False, bpp.opposing_strands)

    def test_convert_insertion(self):
        row = Mock(
            chrom='21', pos=9412306,
            info={
                'SVTYPE': 'INS'
            }, stop=9412400, id=None
        )
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.PINDEL, False)
        self.assertEqual(1, len(bpp_list))
        bpp = bpp_list[0]
        self.assertEqual('21', bpp.break1.chr)
        self.assertEqual('21', bpp.break2.chr)
        self.assertEqual(SVTYPE.INS, bpp.event_type)
        self.assertEqual(row.pos, bpp.break1.start)
        self.assertEqual(row.pos, bpp.break1.end)
        self.assertEqual(row.stop, bpp.break2.start)
        self.assertEqual(row.stop, bpp.break2.end)
        self.assertEqual(ORIENT.LEFT, bpp.break1.orient)
        self.assertEqual(STRAND.NS, bpp.break1.strand)
        self.assertEqual(ORIENT.RIGHT, bpp.break2.orient)
        self.assertEqual(STRAND.NS, bpp.break2.strand)
        self.assertEqual(False, bpp.stranded)
        self.assertEqual(False, bpp.opposing_strands)

    def test_convert_inversion(self):
        row = Mock(
            chrom='21', pos=9412306,
            info={
                'SVTYPE': 'INV'
            }, stop=9412400, id=None
        )
        bpp_list = _convert_tool_row(row, SUPPORTED_TOOL.PINDEL, False)
        self.assertEqual(2, len(bpp_list))
        bpp = sorted(bpp_list, key=lambda x: x.break1)[0]
        self.assertEqual('21', bpp.break1.chr)
        self.assertEqual('21', bpp.break2.chr)
        self.assertEqual(SVTYPE.INV, bpp.event_type)
        self.assertEqual(row.pos, bpp.break1.start)
        self.assertEqual(row.pos, bpp.break1.end)
        self.assertEqual(row.stop, bpp.break2.start)
        self.assertEqual(row.stop, bpp.break2.end)
        self.assertEqual(ORIENT.LEFT, bpp.break1.orient)
        self.assertEqual(STRAND.NS, bpp.break1.strand)
        self.assertEqual(ORIENT.LEFT, bpp.break2.orient)
        self.assertEqual(STRAND.NS, bpp.break2.strand)
        self.assertEqual(False, bpp.stranded)
        self.assertEqual(True, bpp.opposing_strands)


class TestParseBndAlt(unittest.TestCase):
    def test_right(self):
        # '[4:190898243[AGGT'
        chrom, pos, orient, ref, seq = _parse_bnd_alt('[4:190898243[A')
        self.assertEqual('4', chrom)
        self.assertEqual(190898243, pos)
        self.assertEqual(ORIENT.RIGHT, orient)
        self.assertEqual('', seq)
        self.assertEqual('A', ref)

    def test_right_untemp_seq(self):
        chrom, pos, orient, ref, seq = _parse_bnd_alt('[5:190898243[AGGT')
        self.assertEqual('5', chrom)
        self.assertEqual(190898243, pos)
        self.assertEqual(ORIENT.RIGHT, orient)
        self.assertEqual('AGG', seq)
        self.assertEqual('T', ref)

        chrom, pos, orient, ref, seq = _parse_bnd_alt('CAGTNNNCA[5:190898243[')
        self.assertEqual('5', chrom)
        self.assertEqual(190898243, pos)
        self.assertEqual(ORIENT.RIGHT, orient)
        self.assertEqual('AGTNNNCA', seq)
        self.assertEqual('C', ref)

        chrom, pos, orient, ref, seq = _parse_bnd_alt('CTG[21:47575965[')
        self.assertEqual('21', chrom)
        self.assertEqual(47575965, pos)
        self.assertEqual(ORIENT.RIGHT, orient)
        self.assertEqual('TG', seq)
        self.assertEqual('C', ref)

    def test_left(self):
        chrom, pos, orient, ref, seq = _parse_bnd_alt('G]10:198982]')
        self.assertEqual('10', chrom)
        self.assertEqual(198982, pos)
        self.assertEqual(ORIENT.LEFT, orient)
        self.assertEqual('', seq)
        self.assertEqual('G', ref)

        chrom, pos, orient, ref, seq = _parse_bnd_alt(']10:198982]G')
        self.assertEqual('10', chrom)
        self.assertEqual(198982, pos)
        self.assertEqual(ORIENT.LEFT, orient)
        self.assertEqual('', seq)
        self.assertEqual('G', ref)

    def test_left_untemp_seq(self):
        chrom, pos, orient, ref, seq = _parse_bnd_alt(']11:123456]AGTNNNCAT')
        self.assertEqual('11', chrom)
        self.assertEqual(123456, pos)
        self.assertEqual(ORIENT.LEFT, orient)
        self.assertEqual('AGTNNNCA', seq)
        self.assertEqual('T', ref)

        chrom, pos, orient, ref, seq = _parse_bnd_alt(']8:1682443]TGC')
        self.assertEqual('8', chrom)
        self.assertEqual(1682443, pos)
        self.assertEqual(ORIENT.LEFT, orient)
        self.assertEqual('TG', seq)
        self.assertEqual('C', ref)

        chrom, pos, orient, ref, seq = _parse_bnd_alt('AAGTG]11:66289601]')
        self.assertEqual('11', chrom)
        self.assertEqual(66289601, pos)
        self.assertEqual(ORIENT.LEFT, orient)
        self.assertEqual('AGTG', seq)
        self.assertEqual('A', ref)
