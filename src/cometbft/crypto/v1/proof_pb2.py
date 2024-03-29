# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: cometbft/crypto/v1/proof.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from gogoproto import gogo_pb2 as gogoproto_dot_gogo__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='cometbft/crypto/v1/proof.proto',
  package='cometbft.crypto.v1',
  syntax='proto3',
  serialized_options=b'Z3github.com/cometbft/cometbft/api/cometbft/crypto/v1',
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x1e\x63ometbft/crypto/v1/proof.proto\x12\x12\x63ometbft.crypto.v1\x1a\x14gogoproto/gogo.proto\"G\n\x05Proof\x12\r\n\x05total\x18\x01 \x01(\x03\x12\r\n\x05index\x18\x02 \x01(\x03\x12\x11\n\tleaf_hash\x18\x03 \x01(\x0c\x12\r\n\x05\x61unts\x18\x04 \x03(\x0c\"@\n\x07ValueOp\x12\x0b\n\x03key\x18\x01 \x01(\x0c\x12(\n\x05proof\x18\x02 \x01(\x0b\x32\x19.cometbft.crypto.v1.Proof\"6\n\x08\x44ominoOp\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05input\x18\x02 \x01(\t\x12\x0e\n\x06output\x18\x03 \x01(\t\"2\n\x07ProofOp\x12\x0c\n\x04type\x18\x01 \x01(\t\x12\x0b\n\x03key\x18\x02 \x01(\x0c\x12\x0c\n\x04\x64\x61ta\x18\x03 \x01(\x0c\":\n\x08ProofOps\x12.\n\x03ops\x18\x01 \x03(\x0b\x32\x1b.cometbft.crypto.v1.ProofOpB\x04\xc8\xde\x1f\x00\x42\x35Z3github.com/cometbft/cometbft/api/cometbft/crypto/v1b\x06proto3'
  ,
  dependencies=[gogoproto_dot_gogo__pb2.DESCRIPTOR,])




_PROOF = _descriptor.Descriptor(
  name='Proof',
  full_name='cometbft.crypto.v1.Proof',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='total', full_name='cometbft.crypto.v1.Proof.total', index=0,
      number=1, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='index', full_name='cometbft.crypto.v1.Proof.index', index=1,
      number=2, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='leaf_hash', full_name='cometbft.crypto.v1.Proof.leaf_hash', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='aunts', full_name='cometbft.crypto.v1.Proof.aunts', index=3,
      number=4, type=12, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=76,
  serialized_end=147,
)


_VALUEOP = _descriptor.Descriptor(
  name='ValueOp',
  full_name='cometbft.crypto.v1.ValueOp',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='cometbft.crypto.v1.ValueOp.key', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='proof', full_name='cometbft.crypto.v1.ValueOp.proof', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=149,
  serialized_end=213,
)


_DOMINOOP = _descriptor.Descriptor(
  name='DominoOp',
  full_name='cometbft.crypto.v1.DominoOp',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='cometbft.crypto.v1.DominoOp.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='input', full_name='cometbft.crypto.v1.DominoOp.input', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='output', full_name='cometbft.crypto.v1.DominoOp.output', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=215,
  serialized_end=269,
)


_PROOFOP = _descriptor.Descriptor(
  name='ProofOp',
  full_name='cometbft.crypto.v1.ProofOp',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='type', full_name='cometbft.crypto.v1.ProofOp.type', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='key', full_name='cometbft.crypto.v1.ProofOp.key', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='data', full_name='cometbft.crypto.v1.ProofOp.data', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=271,
  serialized_end=321,
)


_PROOFOPS = _descriptor.Descriptor(
  name='ProofOps',
  full_name='cometbft.crypto.v1.ProofOps',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='ops', full_name='cometbft.crypto.v1.ProofOps.ops', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=b'\310\336\037\000', file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=323,
  serialized_end=381,
)

_VALUEOP.fields_by_name['proof'].message_type = _PROOF
_PROOFOPS.fields_by_name['ops'].message_type = _PROOFOP
DESCRIPTOR.message_types_by_name['Proof'] = _PROOF
DESCRIPTOR.message_types_by_name['ValueOp'] = _VALUEOP
DESCRIPTOR.message_types_by_name['DominoOp'] = _DOMINOOP
DESCRIPTOR.message_types_by_name['ProofOp'] = _PROOFOP
DESCRIPTOR.message_types_by_name['ProofOps'] = _PROOFOPS
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Proof = _reflection.GeneratedProtocolMessageType('Proof', (_message.Message,), {
  'DESCRIPTOR' : _PROOF,
  '__module__' : 'cometbft.crypto.v1.proof_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.crypto.v1.Proof)
  })
_sym_db.RegisterMessage(Proof)

ValueOp = _reflection.GeneratedProtocolMessageType('ValueOp', (_message.Message,), {
  'DESCRIPTOR' : _VALUEOP,
  '__module__' : 'cometbft.crypto.v1.proof_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.crypto.v1.ValueOp)
  })
_sym_db.RegisterMessage(ValueOp)

DominoOp = _reflection.GeneratedProtocolMessageType('DominoOp', (_message.Message,), {
  'DESCRIPTOR' : _DOMINOOP,
  '__module__' : 'cometbft.crypto.v1.proof_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.crypto.v1.DominoOp)
  })
_sym_db.RegisterMessage(DominoOp)

ProofOp = _reflection.GeneratedProtocolMessageType('ProofOp', (_message.Message,), {
  'DESCRIPTOR' : _PROOFOP,
  '__module__' : 'cometbft.crypto.v1.proof_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.crypto.v1.ProofOp)
  })
_sym_db.RegisterMessage(ProofOp)

ProofOps = _reflection.GeneratedProtocolMessageType('ProofOps', (_message.Message,), {
  'DESCRIPTOR' : _PROOFOPS,
  '__module__' : 'cometbft.crypto.v1.proof_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.crypto.v1.ProofOps)
  })
_sym_db.RegisterMessage(ProofOps)


DESCRIPTOR._options = None
_PROOFOPS.fields_by_name['ops']._options = None
# @@protoc_insertion_point(module_scope)
