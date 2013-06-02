#!/usr/bin/python
# DirectX Shader Bytecode Disassembler
# Mainly for use with vs_3_0 / ps_3_0
# Some instructions have the same opcode but more or fewer source registers when used
# by older shader versions.  We don't really test for that here so it'll break!

# The main goal is to turn compiled bytecode into something more understandable
# The output isn't necessarily meant to be able to be recompiled as-is

import sys
import struct

# opcodes for pixel and vertex shaders
D3DSIO_NOP          =  0
D3DSIO_MOV          =  1
D3DSIO_ADD          =  2
D3DSIO_SUB          =  3
D3DSIO_MAD          =  4
D3DSIO_MUL          =  5
D3DSIO_RCP          =  6
D3DSIO_RSQ          =  7
D3DSIO_DP3          =  8
D3DSIO_DP4          =  9
D3DSIO_MIN          = 10
D3DSIO_MAX          = 11
D3DSIO_SLT          = 12
D3DSIO_SGE          = 13
D3DSIO_EXP          = 14
D3DSIO_LOG          = 15
D3DSIO_LIT          = 16
D3DSIO_DST          = 17
D3DSIO_LRP          = 18
D3DSIO_FRC          = 19
D3DSIO_M4x4         = 20
D3DSIO_M4x3         = 21
D3DSIO_M3x4         = 22
D3DSIO_M3x3         = 23
D3DSIO_M3x2         = 24
D3DSIO_CALL         = 25
D3DSIO_CALLNZ       = 26
D3DSIO_LOOP         = 27
D3DSIO_RET          = 28
D3DSIO_ENDLOOP      = 29
D3DSIO_LABEL        = 30
D3DSIO_DCL          = 31
D3DSIO_POW          = 32
D3DSIO_CRS          = 33
D3DSIO_SGN          = 34
D3DSIO_ABS          = 35
D3DSIO_NRM          = 36
D3DSIO_SINCOS       = 37
D3DSIO_REP          = 38
D3DSIO_ENDREP       = 39
D3DSIO_IF           = 40
D3DSIO_IFC          = 41
D3DSIO_ELSE         = 42
D3DSIO_ENDIF        = 43
D3DSIO_BREAK        = 44
D3DSIO_BREAKC       = 45
D3DSIO_MOVA         = 46
D3DSIO_DEFB         = 47
D3DSIO_DEFI         = 48

D3DSIO_TEXCOORD     = 64
D3DSIO_TEXKILL      = 65
D3DSIO_TEX          = 66
D3DSIO_TEXBEM       = 67
D3DSIO_TEXBEML      = 68
D3DSIO_TEXREG2AR    = 69
D3DSIO_TEXREG2GB    = 70
D3DSIO_TEXM3x2PAD   = 71
D3DSIO_TEXM3x2TEX   = 72
D3DSIO_TEXM3x3PAD   = 73
D3DSIO_TEXM3x3TEX   = 74
D3DSIO_TEXM3x3DIFF  = 75
D3DSIO_TEXM3x3SPEC  = 76
D3DSIO_TEXM3x3VSPEC = 77
D3DSIO_EXPP         = 78
D3DSIO_LOGP         = 79
D3DSIO_CND          = 80
D3DSIO_DEF          = 81
D3DSIO_TEXREG2RGB   = 82
D3DSIO_TEXDP3TEX    = 83
D3DSIO_TEXM3x2DEPTH = 84
D3DSIO_TEXDP3       = 85
D3DSIO_TEXM3x3      = 86
D3DSIO_TEXDEPTH     = 87
D3DSIO_CMP          = 88
D3DSIO_BEM          = 89
D3DSIO_DP2ADD       = 90
D3DSIO_DSX          = 91
D3DSIO_DSY          = 92
D3DSIO_TEXLDD       = 93
D3DSIO_SETP         = 94
D3DSIO_TEXLDL       = 95
D3DSIO_BREAKP       = 96
D3DSIO_PHASE        = 0xFFFD
D3DSIO_COMMENT      = 0xFFFE
D3DSIO_END          = 0XFFFF

D3DSIO = {
	D3DSIO_NOP: {'op':'nop'},
	D3DSIO_MOV: {'op':'mov', 'gen':lambda tok: MovInstruction(tok)},
	D3DSIO_ADD: {'op':'add', 'gen':lambda tok: AddInstruction(tok)},
	D3DSIO_SUB: {'op':'sub', 'gen':lambda tok: SubInstruction(tok)},
	D3DSIO_MAD: {'op':'mad', 'gen':lambda tok: MadInstruction(tok)},
	D3DSIO_MUL: {'op':'mul', 'gen':lambda tok: MulInstruction(tok)},
	D3DSIO_RCP: {'op':'rcp', 'gen':lambda tok: RcpInstruction(tok)},
	D3DSIO_RSQ: {'op':'rsq', 'gen':lambda tok: RsqInstruction(tok)},
	D3DSIO_DP3: {'op':'dp3', 'gen':lambda tok: Dp3Instruction(tok)},
	D3DSIO_DP4: {'op':'dp4', 'gen':lambda tok: Dp4Instruction(tok)},
	D3DSIO_MIN: {'op':'min', 'gen':lambda tok: MinInstruction(tok)},
	D3DSIO_MAX: {'op':'max', 'gen':lambda tok: MaxInstruction(tok)},
	D3DSIO_SLT: {'op':'slt', 'gen':lambda tok: SltInstruction(tok)},
	D3DSIO_SGE: {'op':'sge', 'gen':lambda tok: SgeInstruction(tok)},
	D3DSIO_EXP: {'op':'exp', 'gen':lambda tok: ExpInstruction(tok)},
	D3DSIO_LOG: {'op':'log', 'gen':lambda tok: LogInstruction(tok)},
	D3DSIO_LIT: {'op':'lit', 'gen':lambda tok: LitInstruction(tok)},
	D3DSIO_DST: {'op':'dst', 'gen':lambda tok: DstInstruction(tok)},
	D3DSIO_LRP: {'op':'lrp', 'gen':lambda tok: LrpInstruction(tok)},
	D3DSIO_FRC: {'op':'frc', 'gen':lambda tok: FrcInstruction(tok)},
	D3DSIO_M4x4: {'op':'m4x4', 'gen':lambda tok: M4x4Instruction(tok)},
	D3DSIO_M4x3: {'op':'m4x3', 'gen':lambda tok: M4x3Instruction(tok)},
	D3DSIO_M3x4: {'op':'m3x4', 'gen':lambda tok: M3x4Instruction(tok)},
	D3DSIO_M3x3: {'op':'m3x3', 'gen':lambda tok: M3x3Instruction(tok)},
	D3DSIO_M3x2: {'op':'m3x2', 'gen':lambda tok: M3x2Instruction(tok)},
	D3DSIO_CALL: {'op':'call', 'gen':lambda tok: CallInstruction(tok)},
	D3DSIO_CALLNZ: {'op':'callnz', 'gen':lambda tok: CallNzInstruction(tok)},
	D3DSIO_LOOP: {'op':'loop', 'gen':lambda tok: LoopInstruction(tok)},
	D3DSIO_RET: {'op':'ret'},
	D3DSIO_ENDLOOP: {'op':'endloop'},
	D3DSIO_LABEL: {'op':'label', 'gen':lambda tok: LabelInstruction(tok)},
	D3DSIO_DCL: {'op':'dcl', 'gen':lambda tok: DclInstruction(tok)},
	D3DSIO_POW: {'op':'pow', 'gen':lambda tok: PowInstruction(tok)},
	D3DSIO_CRS: {'op':'crs', 'gen':lambda tok: CrsInstruction(tok)},
	D3DSIO_SGN: {'op':'sgn', 'gen':lambda tok: SgnInstruction(tok)},
	D3DSIO_ABS: {'op':'abs', 'gen':lambda tok: AbsInstruction(tok)},
	D3DSIO_NRM: {'op':'nrm', 'gen':lambda tok: NrmInstruction(tok)},
	D3DSIO_SINCOS: {'op':'sincos', 'gen':lambda tok: SinCosInstruction(tok)},
	D3DSIO_REP: {'op':'rep', 'gen':lambda tok: RepInstruction(tok)},
	D3DSIO_ENDREP: {'op':'endrep'},
	D3DSIO_IF: {'op':'if', 'gen':lambda tok: IfInstruction(tok)},
	D3DSIO_IFC: {'op':'ifc', 'gen':lambda tok: IfCompInstruction(tok)},
	D3DSIO_ELSE: {'op':'else'},
	D3DSIO_ENDIF: {'op':'endif'},
	D3DSIO_BREAK: {'op':'break'},
	D3DSIO_BREAKC: {'op':'breakc', 'gen':lambda tok: BreakCInstruction(tok)},
	D3DSIO_MOVA: {'op':'mova', 'gen':lambda tok: MovaInstruction(tok)},
	D3DSIO_DEFB: {'op':'defb', 'gen':lambda tok: DefBInstruction(tok)},
	D3DSIO_DEFI: {'op':'defi', 'gen':lambda tok: DefIInstruction(tok)},
	D3DSIO_TEXCOORD: {'op':'texcoord', 'gen':lambda tok: TexCoordInstruction(tok)},
	D3DSIO_TEXKILL: {'op':'texkill', 'gen':lambda tok: TexKillInstruction(tok)},
	D3DSIO_TEX: {'op':'tex', 'gen':lambda tok: TexInstruction(tok)},
	D3DSIO_TEXBEM: {'op':'texbem', 'gen':lambda tok: TexBemInstruction(tok)},
	D3DSIO_TEXBEML: {'op':'texbeml', 'gen':lambda tok: TexBemlInstruction(tok)},
	D3DSIO_TEXREG2AR: {'op':'texreg2ar', 'gen':lambda tok: TexReg2ARInstruction(tok)},
	D3DSIO_TEXREG2GB: {'op':'texreg2gb', 'gen':lambda tok: TexReg2GBInstruction(tok)},
	D3DSIO_TEXM3x2PAD: {'op':'texm3x2pad', 'gen':lambda tok: TexM3x2PadInstruction(tok)},
	D3DSIO_TEXM3x2TEX: {'op':'texm3x2tex', 'gen':lambda tok: TexM3x2TexInstruction(tok)},
	D3DSIO_TEXM3x3PAD: {'op':'texm3x3pad', 'gen':lambda tok: TexM3x3PadInstruction(tok)},
	D3DSIO_TEXM3x3TEX: {'op':'texm3x3tex', 'gen':lambda tok: TexM3x3TexInstruction(tok)},
	D3DSIO_TEXM3x3DIFF: {'op':'texm3x3diff'},
	D3DSIO_TEXM3x3SPEC: {'op':'texm3x3spec', 'gen':lambda tok: TexM3x3SpecInstruction(tok)},
	D3DSIO_TEXM3x3VSPEC: {'op':'texm3x3vspec', 'gen':lambda tok: TexM3x3VSpecInstruction(tok)},
	D3DSIO_EXPP: {'op':'expp', 'gen':lambda tok: ExppInstruction(tok)},
	D3DSIO_LOGP: {'op':'logp', 'gen':lambda tok: LogpInstruction(tok)},
	D3DSIO_CND: {'op':'cnd', 'gen':lambda tok: CndInstruction(tok)},
	D3DSIO_DEF: {'op':'def', 'gen':lambda tok: DefInstruction(tok)},
	D3DSIO_TEXREG2RGB: {'op':'texreg2rgb', 'gen':lambda tok: TexReg2RGBInstruction(tok)},
	D3DSIO_TEXDP3TEX: {'op':'texdp3tex', 'gen':lambda tok: TexDp3TexInstruction(tok)},
	D3DSIO_TEXM3x2DEPTH: {'op':'texm3x2depth', 'gen':lambda tok: TexM3x2DepthInstruction(tok)},
	D3DSIO_TEXDP3: {'op':'texdp3', 'gen':lambda tok: TexDp3Instruction(tok)},
	D3DSIO_TEXM3x3: {'op':'texm3x3', 'gen':lambda tok: TexM3x3Instruction(tok)},
	D3DSIO_TEXDEPTH: {'op':'texdepth', 'gen':lambda tok: TexDepthInstruction(tok)},
	D3DSIO_CMP: {'op':'cmp', 'gen':lambda tok: CmpInstruction(tok)},
	D3DSIO_BEM: {'op':'bem', 'gen':lambda tok: BemInstruction(tok)},
	D3DSIO_DP2ADD: {'op':'dp2add', 'gen':lambda tok: Dp2AddInstruction(tok)},
	D3DSIO_DSX: {'op':'dsx', 'gen':lambda tok: DsxInstruction(tok)},
	D3DSIO_DSY: {'op':'dsy', 'gen':lambda tok: DsyInstruction(tok)},
	D3DSIO_TEXLDD: {'op':'texldd', 'gen':lambda tok: TexLddInstruction(tok)},
	D3DSIO_SETP: {'op':'setp', 'gen':lambda tok: SetpInstruction(tok)},
	D3DSIO_TEXLDL: {'op':'texldl', 'gen':lambda tok: TexLdlInstruction(tok)},
	D3DSIO_BREAKP: {'op':'breakp', 'gen':lambda tok: BreakPInstruction(tok)},
	D3DSIO_PHASE: {'op':'phase'},
	D3DSIO_COMMENT: {'op':'comment'},
	D3DSIO_END: {'op':'end'}
}

# Register Types
D3DSPR_TEMP = 0
D3DSPR_INPUT = 1
D3DSPR_CONST = 2
D3DSPR_TEXTURE = 3
D3DSPR_ADDR = 3
D3DSPR_RASTOUT = 4
D3DSPR_ATTROUT = 5
D3DSPR_TEXCRDOUT = 6
D3DSPR_OUTPUT = 6
D3DSPR_CONSTINT = 7
D3DSPR_COLOROUT = 8
D3DSPR_DEPTHOUT = 9
D3DSPR_SAMPLER = 10
D3DSPR_CONST2 = 11
D3DSPR_CONST3 = 12
D3DSPR_CONST4 = 13
D3DSPR_CONSTBOOL = 14
D3DSPR_LOOP = 15
D3DSPR_TEMPFLOAT16 = 16
D3DSPR_MISCTYPE = 17
D3DSPR_LABEL = 18
D3DSPR_PREDICATE = 19

# D3DDECLUSAGE
D3DDECLUSAGE_POSITION = 0
D3DDECLUSAGE_BLENDWEIGHT = 1
D3DDECLUSAGE_BLENDINDICES = 2
D3DDECLUSAGE_NORMAL = 3
D3DDECLUSAGE_PSIZE = 4
D3DDECLUSAGE_TEXCOORD = 5
D3DDECLUSAGE_TANGENT = 6
D3DDECLUSAGE_BINORMAL = 7
D3DDECLUSAGE_TESSFACTOR = 8
D3DDECLUSAGE_POSITIONT = 9
D3DDECLUSAGE_COLOR = 10
D3DDECLUSAGE_FOG = 11
D3DDECLUSAGE_DEPTH = 12
D3DDECLUSAGE_SAMPLE = 13

D3DDECLUSAGE = {
	D3DDECLUSAGE_POSITION: {'text':'position'},
	D3DDECLUSAGE_BLENDWEIGHT: {'text':'blendweight'},
	D3DDECLUSAGE_BLENDINDICES: {'text':'blendindices'},
	D3DDECLUSAGE_NORMAL: {'text':'normal'},
	D3DDECLUSAGE_PSIZE: {'text':'psize'},
	D3DDECLUSAGE_TEXCOORD: {'text':'texcoord'},
	D3DDECLUSAGE_TANGENT: {'text':'tangent'},
	D3DDECLUSAGE_BINORMAL: {'text':'binormal'},
	D3DDECLUSAGE_TESSFACTOR: {'text':'tessfactor'},
	D3DDECLUSAGE_POSITIONT: {'text':'positiont'},
	D3DDECLUSAGE_COLOR: {'text':'color'},
	D3DDECLUSAGE_FOG: {'text':'fog'},
	D3DDECLUSAGE_DEPTH: {'text':'depth'},
	D3DDECLUSAGE_SAMPLE: {'text':'sample'},
}

#D3DSAMPLER_TEXTURE_TYPE
D3DSTT_UNKNOWN = 0
D3DSTT_1D = 1
D3DSTT_2D = 2
D3DSTT_CUBE = 3
D3DSTT_VOLUME = 4

D3DSTT = {
	D3DSTT_UNKNOWN: {'text':'unknown'},
	D3DSTT_1D: {'text':'1d'},
	D3DSTT_2D: {'text':'2d'},
	D3DSTT_CUBE: {'text':'cube'},
	D3DSTT_VOLUME: {'text':'volume'}
}

SOURCE_MOD_FORMAT = {
	0 : '%s',
	1 : '-%s',
	2 : '%s_bias',
	3 : '-%s_bias',
	4 : '%s_bx2',
	5 : '-%s_bx2',
	6 : '1-%s',
	7 : '%s_x2',
	8 : '-%s_x2',
	9 : '%s_dz',
	10: '%s_dw',
	11: 'abs(%s)',
	12: '-abs(%s)',
	13: 'NOT %s'
}
SHADERTYPE_VERTEX = 0xFFFE
SHADERTYPE_PIXEL = 0xFFFF

gCurrentShaderType = SHADERTYPE_VERTEX

class TokenStreamError(Exception):
	"""Exception raised when an unexpected value was found in the bytecode stream"""
	pass

class InstructionToken:
	def __init__(self, instructionToken):
		self.op = instructionToken & 0xffff
		self.flags = (instructionToken >> 16) & 0xff
		self.length = (instructionToken >> 24) & 0xf
		self.predicated = (instructionToken >> 28) & 0x1
		self.coissue = (instructionToken >> 30) & 0x1
		# print "Debug: %08X, %d, %d, %d, %d, %d" % (instructionToken, self.op, self.flags, self.length, self.predicated, self.coissue)
	def size(self):
		"""Size in bytes of the instruction in the byte stream"""
		return (self.length + 1) * 4
	def create_instruction(self, stream, offset):
		if 'gen' in D3DSIO[self.op]:
			inst = D3DSIO[self.op]['gen'](self)
		else:
			inst = Instruction(self)
		inst.load(stream, offset)
		return inst
	def is_exit(self):
		return (self.op == D3DSIO_END)
	def mnemonic(self):
		return D3DSIO[self.op]['op']

RegisterMnemonicLookupVS = {
	D3DSPR_CONST : 'c',
	D3DSPR_TEMP : 'r',
	D3DSPR_INPUT : 'v',
	D3DSPR_ADDR : 'a',
	D3DSPR_RASTOUT : 'rast',
	D3DSPR_ATTROUT : 'attr',
	D3DSPR_OUTPUT : 'o',
	D3DSPR_CONSTINT : 'i',
	D3DSPR_COLOROUT : 'oC',
	D3DSPR_DEPTHOUT : 'oDepth',
	D3DSPR_SAMPLER : 's',
	D3DSPR_CONST2 : 'c',
	D3DSPR_CONST3 : 'c',
	D3DSPR_CONST4 : 'c',
	D3DSPR_CONSTBOOL : 'b',
	D3DSPR_LOOP : 'aL',
	D3DSPR_PREDICATE : 'p'
}
RegisterMnemonicLookupPS = {
	D3DSPR_CONST : 'c',
	D3DSPR_TEMP : 'r',
	D3DSPR_INPUT : 'v',
	D3DSPR_TEXTURE : 't',
	D3DSPR_RASTOUT : 'rast',
	D3DSPR_ATTROUT : 'attr',
	D3DSPR_OUTPUT : 'o',
	D3DSPR_CONSTINT : 'i',
	D3DSPR_COLOROUT : 'oC',
	D3DSPR_DEPTHOUT : 'oDepth',
	D3DSPR_SAMPLER : 's',
	D3DSPR_CONST2 : 'c',
	D3DSPR_CONST3 : 'c',
	D3DSPR_CONST4 : 'c',
	D3DSPR_CONSTBOOL : 'b',
	D3DSPR_LOOP : 'aL',
	D3DSPR_PREDICATE : 'p',
	D3DSPR_MISCTYPE : 'm'
}
class ParameterToken:
	def swizzle_text():
		return ''
	def debug_print():
		print 'You should override debug_print for anything that inherits from ParameterToken'
	def to_string(self):
		reg_str = 'unk'
		if gCurrentShaderType == SHADERTYPE_VERTEX:
			reg_str = RegisterMnemonicLookupVS[self.register_type]
		else:
			reg_str = RegisterMnemonicLookupPS[self.register_type]

		if self.is_relative:
			if self.relative_param is None:
				return "!ERR!"
			out = reg_str
			if self.register > 0:
				out += "%d" % self.register
			out += "["
			if self.relative_param.register_type == D3DSPR_LOOP:
				out += "aL%s" % (self.relative_param.swizzle_text())
			elif self.relative_param.register_type == D3DSPR_ADDR:
				out += "a%d%s" % (self.relative_param.register, self.relative_param.swizzle_text())
			else:
				raise TokenStreamError("Invalid relative addressing parameter found")
			out += "]"
			return out
		else:
			if self.register_type == D3DSPR_LOOP:
				return "aL%s" % (self.register, self.swizzle_text())
			elif self.register_type == D3DSPR_DEPTHOUT:
				return "oDepth%s" % (self.register, self.swizzle_text())
			else:
				return "%s%d%s" % (reg_str, self.register, self.swizzle_text())
		self.debug_print()
		return "unk_reg"

class DestinationParameterToken(ParameterToken):
	def __init__(self, val):
		self.force_swizzle = False
		self.register = (val & 0x7ff)
		register_type_34 = (val >> 11) & 0x3
		self.is_relative = (val >> 13) & 0x1
		self.write_mask = (val >> 16) & 0xf
		self.result_modifier = (val >> 20) & 0xf
		self.shift_scale = (val >> 24) & 0xf
		register_type_012 = (val >> 28) & 0x7
		self.register_type = (register_type_34 << 3) + register_type_012
		self.relative_param = None
	def debug_print(self):
		print "Dst: %d, %d, %d, %d, %d, %d" % (self.register, self.register_type, self.write_mask, self.is_relative, self.result_modifier, self.shift_scale)
	def mod_str(self):
		str = ''
		if (self.result_modifier & 0x1) == 0x1:
			str += '_sat'
		if (self.result_modifier & 0x2) == 0x2:
			str += '_pp'
		if (self.result_modifier & 0x4) == 0x4:
			str += '_centroid'
		return str
	def swizzle_text(self):
		if (self.write_mask == 15) and not self.force_swizzle:
			return ''
		mask = '.'
		if self.write_mask & 0x1 == 0x1:
			mask += 'x'
		if self.write_mask & 0x2 == 0x2:
			mask += 'y'
		if self.write_mask & 0x4 == 0x4:
			mask += 'z'
		if self.write_mask & 0x8 == 0x8:
			mask += 'w'
		return mask

class SourceParameterToken(ParameterToken):
	def __init__(self, val):
		self.force_swizzle = False
		self.register = (val & 0x7ff)
		register_type_34 = (val >> 11) & 0x3
		self.is_relative = (val >> 13) & 0x1
		self.read_mask = (val >> 16) & 0xff
		self.source_modifier = (val >> 24) & 0xf
		register_type_012 = (val >> 28) & 0x7
		self.register_type = (register_type_34 << 3) + register_type_012
		self.relative_param = None
	def debug_print(self):
		print "Src: %d, %d, %d, %d, %d" % (self.register, self.register_type, self.read_mask, self.is_relative, self.source_modifier)
	def mod_str(self, str):
		return SOURCE_MOD_FORMAT[self.source_modifier] % str
	def swizzle_component_str(self, val):
		if val == 0:
			return 'x'
		if val == 1:
			return 'y'
		if val == 2:
			return 'z'
		if val == 3:
			return 'w'
	def swizzle_text(self):
		if (self.read_mask == 0xE4) and not self.force_swizzle:
			return ''
		last_val = (self.read_mask >> 6) & 0x3
		mask = self.swizzle_component_str(last_val)
		ch = 0
		# Do this in reverse order
		# We don't need to specify the last swizzle values if they're duplicated
		# e.g. r0.x is equivalent to r0.xxxx, r0.xy is equivalent to r0.xyyy
		for i in xrange(3):
			val = (self.read_mask >> (4 - 2*i)) & 0x3
			if (val != last_val) or ch:
				mask = self.swizzle_component_str(val) + mask
				ch = 1
		return '.' + mask
	def to_string(self):
		return self.mod_str(ParameterToken.to_string(self))

class Instruction:
	def __init__(self, token):
		self.token = token
	def size(self):
		return self.token.size()
	def load(self, stream, offset):
		return
	def mnemonic(self, dst=None):
		mn = self.token.mnemonic()
		if dst is not None:
			mn += dst.mod_str()
		return mn
	def to_string(self):
		return self.mnemonic()

class AbsInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class AddInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class BemInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class BreakCInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(), self.src0.to_string(), self.src1.to_string())

class BreakPInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s" % (self.mnemonic(), self.src.to_string())

class CallInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s" % (self.mnemonic(), self.src.to_string())

class CallNzInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(), self.src0.to_string(), self.src1.to_string())

class CmpInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
		self.src2, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string(), self.src2.to_string())

class CndInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
		self.src2, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string(), self.src2.to_string())

class CrsInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class DclInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		params = struct.unpack('<I', stream[offset+4:offset+8])[0]
		offset += 8
		self.dst, offset = get_destination_param(stream, offset)
		if self.dst.register_type == D3DSPR_INPUT or self.dst.register_type == D3DSPR_OUTPUT or self.dst.register_type == D3DSPR_TEXTURE:
			self.usage = params & 0x1f
			self.usage_index = (params >> 16) & 0xf
		if self.dst.register_type == D3DSPR_SAMPLER:
			self.texture_type = (params >> 27) & 0xf
	def mnemonic(self):
		mn = "dcl"
		if self.dst.register_type == D3DSPR_INPUT or self.dst.register_type == D3DSPR_OUTPUT or self.dst.register_type == D3DSPR_TEXTURE:
			mn = "dcl_%s%d" % (D3DDECLUSAGE[self.usage]['text'], self.usage_index)
		elif self.dst.register_type == D3DSPR_SAMPLER:
			mn = "dcl_%s" % D3DSTT[self.texture_type]['text']
		return mn + self.dst.mod_str()
	def to_string(self):
		return "%s %s" % (self.mnemonic(), self.dst.to_string())

class DefInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.values = struct.unpack('<ffff', stream[offset:offset+16])
	def to_string(self):
		return "%s %s, %f, %f, %f, %f" % (self.mnemonic(self.dst), self.dst.to_string(), self.values[0], self.values[1], self.values[2], self.values[3])

class DefBInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.value = struct.unpack('<I', stream[offset:offset+4])[0]
	def to_string(self):
		return "%s %s %s" % (self.mnemonic(self.dst), self.dst.to_string(), "FALSE" if self.value == 0 else "TRUE")

class DefIInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.values = struct.unpack('<iiii', stream[offset:offset+16])
	def to_string(self):
		return "%s %s %d, %d, %d, %d" % (self.mnemonic(self.dst), self.dst.to_string(), self.values[0], self.values[1], self.values[2], self.values[3])

class Dp2AddInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
		self.src2, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string(), self.src2.to_string())

class Dp3Instruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class Dp4Instruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class DstInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class DsxInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class DsyInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class ExpInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class ExppInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class FrcInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class IfInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s" % (self.mnemonic(), self.src.to_string())

class IfCompInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(), self.src0.to_string(), self.src1.to_string())

class LabelInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s" % (self.mnemonic(), self.src.to_string())

class LitInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class LogInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class LogPInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class LoopInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(), self.src0.to_string(), self.src1.to_string())

class LrpInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
		self.src2, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string(), self.src2.to_string())

class M3x2Instruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class M3x3Instruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class M3x4Instruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class M4x3Instruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class M4x4Instruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class MadInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
		self.src2, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string(), self.src2.to_string())

class MaxInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class MinInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class MovInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class MovaInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class MulInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset) # DestinationParameterToken(data[0])
		self.src0, offset = get_source_param(stream, offset) # = SourceParameterToken(data[1])
		self.src1, offset = get_source_param(stream, offset) # = SourceParameterToken(data[2])
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class NrmInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class PowInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class RcpInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class RepInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s" % (self.mnemonic(), self.src.to_string())

class RsqInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class SetpInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class SgeInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class SgnInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
		self.src2, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string(), self.src2.to_string())

class SinCosInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class SltInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class SubInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class TexInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class TexBemInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexBemlInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexCoordInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
	def to_string(self):
		return "%s %s" % (self.mnemonic(self.dst), self.dst.to_string())

class TexDepthInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
	def to_string(self):
		return "%s %s" % (self.mnemonic(self.dst), self.dst.to_string())

class TexDp3Instruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexDp3TexInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexKillInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
	def to_string(self):
		return "%s %s" % (self.mnemonic(self.dst), self.dst.to_string())

class TexLddInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
		self.src2, offset = get_source_param(stream, offset)
		self.src3, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string(), self.src2.to_string(), self.src3.to_string())

class TexLdlInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class TexM3x2DepthInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexM3x2PadInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexM3x2TexInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexM3x3Instruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexM3x3PadInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexM3x3SpecInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src0, offset = get_source_param(stream, offset)
		self.src1, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src0.to_string(), self.src1.to_string())

class TexM3x3TexInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexM3x3VSpecInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexReg2ARInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexReg2GBInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		#data = struct.unpack('<II', stream[offset+4:offset+12])
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

class TexReg2RGBInstruction(Instruction):
	def __init__(self, token):
		Instruction.__init__(self, token)
	def load(self, stream, offset):
		data = struct.unpack('<II', stream[offset+4:offset+12])
		offset += 4
		self.dst, offset = get_destination_param(stream, offset)
		self.src, offset = get_source_param(stream, offset)
	def to_string(self):
		return "%s %s, %s" % (self.mnemonic(self.dst), self.dst.to_string(), self.src.to_string())

# Get the next instruction from the bytecode stream
def get_instruction(stream, offset):
	instTokenValue = struct.unpack('<I', stream[offset:offset+4])[0]
	instToken = InstructionToken(instTokenValue)
	inst = instToken.create_instruction(stream, offset)
	return inst

def get_source_param(stream, offset):
	tokenValue = struct.unpack('<I', stream[offset:offset+4])[0]
	param = SourceParameterToken(tokenValue)
	offset += 4
	if param.is_relative:
		param.relative_param, offset = get_source_param(stream, offset)
	return param, offset

def get_destination_param(stream, offset):
	tokenValue = struct.unpack('<I', stream[offset:offset+4])[0]
	param = DestinationParameterToken(tokenValue)
	offset += 4
	if param.is_relative:
		param.relative_param, offset = get_destination_param(stream, offset)
	return param, offset

def get_version(stream):
	val = struct.unpack('<I', stream[:4])[0]
	if ((val >> 16) & 0xfffe) != 0xfffe:
		raise TokenStreamError("Version error, unknown shader type")
	minorVersion = val & 0xff
	majorVersion = (val >> 8) & 0xff
	shaderType = (val >> 16) & 0xffff
	return (shaderType, majorVersion, minorVersion)

def disassemble(bytecode, isDebug):
	global gCurrentShaderType
	shaderType, majorVersion, minorVersion = get_version(bytecode)
	gCurrentShaderType = shaderType
	print "%s_%d_%d" % (('vs' if (shaderType == SHADERTYPE_VERTEX) else 'ps'), majorVersion, minorVersion)
	offset = 4
	while offset < len(bytecode):
		inst = get_instruction(bytecode, offset)
		if isDebug:
			print "; Offset 0x%X" % offset
		print inst.to_string()
		offset += inst.size()

def print_usage():
	print "Usage: dxshd.py [-d] <file>"
	print "File should contain only DirectX shader bytecode"

def main(argc, argv):
	if (argc < 2):
		print_usage()
		return
	isDebug = False
	fileName = ''
	if (argv[1] == '-d'):
		isDebug = True
		if (argc < 3):
			print_usage()
			return
		fileName = argv[2]
	else:
		fileName = argv[1]
	shaderFile = open(fileName, 'rb')
	shaderBytecode = shaderFile.read()
	disassemble(shaderBytecode, isDebug)

if __name__=="__main__":
	main(len(sys.argv), sys.argv)