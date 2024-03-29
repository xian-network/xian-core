# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: cometbft/services/pruning/v1/pruning.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='cometbft/services/pruning/v1/pruning.proto',
  package='cometbft.services.pruning.v1',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n*cometbft/services/pruning/v1/pruning.proto\x12\x1c\x63ometbft.services.pruning.v1\"-\n\x1bSetBlockRetainHeightRequest\x12\x0e\n\x06height\x18\x01 \x01(\x04\"\x1e\n\x1cSetBlockRetainHeightResponse\"\x1d\n\x1bGetBlockRetainHeightRequest\"`\n\x1cGetBlockRetainHeightResponse\x12\x19\n\x11\x61pp_retain_height\x18\x01 \x01(\x04\x12%\n\x1dpruning_service_retain_height\x18\x02 \x01(\x04\"4\n\"SetBlockResultsRetainHeightRequest\x12\x0e\n\x06height\x18\x01 \x01(\x04\"%\n#SetBlockResultsRetainHeightResponse\"$\n\"GetBlockResultsRetainHeightRequest\"L\n#GetBlockResultsRetainHeightResponse\x12%\n\x1dpruning_service_retain_height\x18\x01 \x01(\x04\"1\n\x1fSetTxIndexerRetainHeightRequest\x12\x0e\n\x06height\x18\x01 \x01(\x04\"\"\n SetTxIndexerRetainHeightResponse\"!\n\x1fGetTxIndexerRetainHeightRequest\"2\n GetTxIndexerRetainHeightResponse\x12\x0e\n\x06height\x18\x01 \x01(\x04\"4\n\"SetBlockIndexerRetainHeightRequest\x12\x0e\n\x06height\x18\x01 \x01(\x04\"%\n#SetBlockIndexerRetainHeightResponse\"$\n\"GetBlockIndexerRetainHeightRequest\"5\n#GetBlockIndexerRetainHeightResponse\x12\x0e\n\x06height\x18\x01 \x01(\x04\x62\x06proto3'
)




_SETBLOCKRETAINHEIGHTREQUEST = _descriptor.Descriptor(
  name='SetBlockRetainHeightRequest',
  full_name='cometbft.services.pruning.v1.SetBlockRetainHeightRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='height', full_name='cometbft.services.pruning.v1.SetBlockRetainHeightRequest.height', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
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
  serialized_end=121,
)


_SETBLOCKRETAINHEIGHTRESPONSE = _descriptor.Descriptor(
  name='SetBlockRetainHeightResponse',
  full_name='cometbft.services.pruning.v1.SetBlockRetainHeightResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
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
  serialized_start=123,
  serialized_end=153,
)


_GETBLOCKRETAINHEIGHTREQUEST = _descriptor.Descriptor(
  name='GetBlockRetainHeightRequest',
  full_name='cometbft.services.pruning.v1.GetBlockRetainHeightRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
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
  serialized_start=155,
  serialized_end=184,
)


_GETBLOCKRETAINHEIGHTRESPONSE = _descriptor.Descriptor(
  name='GetBlockRetainHeightResponse',
  full_name='cometbft.services.pruning.v1.GetBlockRetainHeightResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='app_retain_height', full_name='cometbft.services.pruning.v1.GetBlockRetainHeightResponse.app_retain_height', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='pruning_service_retain_height', full_name='cometbft.services.pruning.v1.GetBlockRetainHeightResponse.pruning_service_retain_height', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=186,
  serialized_end=282,
)


_SETBLOCKRESULTSRETAINHEIGHTREQUEST = _descriptor.Descriptor(
  name='SetBlockResultsRetainHeightRequest',
  full_name='cometbft.services.pruning.v1.SetBlockResultsRetainHeightRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='height', full_name='cometbft.services.pruning.v1.SetBlockResultsRetainHeightRequest.height', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=284,
  serialized_end=336,
)


_SETBLOCKRESULTSRETAINHEIGHTRESPONSE = _descriptor.Descriptor(
  name='SetBlockResultsRetainHeightResponse',
  full_name='cometbft.services.pruning.v1.SetBlockResultsRetainHeightResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
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
  serialized_start=338,
  serialized_end=375,
)


_GETBLOCKRESULTSRETAINHEIGHTREQUEST = _descriptor.Descriptor(
  name='GetBlockResultsRetainHeightRequest',
  full_name='cometbft.services.pruning.v1.GetBlockResultsRetainHeightRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
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
  serialized_start=377,
  serialized_end=413,
)


_GETBLOCKRESULTSRETAINHEIGHTRESPONSE = _descriptor.Descriptor(
  name='GetBlockResultsRetainHeightResponse',
  full_name='cometbft.services.pruning.v1.GetBlockResultsRetainHeightResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='pruning_service_retain_height', full_name='cometbft.services.pruning.v1.GetBlockResultsRetainHeightResponse.pruning_service_retain_height', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=415,
  serialized_end=491,
)


_SETTXINDEXERRETAINHEIGHTREQUEST = _descriptor.Descriptor(
  name='SetTxIndexerRetainHeightRequest',
  full_name='cometbft.services.pruning.v1.SetTxIndexerRetainHeightRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='height', full_name='cometbft.services.pruning.v1.SetTxIndexerRetainHeightRequest.height', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=493,
  serialized_end=542,
)


_SETTXINDEXERRETAINHEIGHTRESPONSE = _descriptor.Descriptor(
  name='SetTxIndexerRetainHeightResponse',
  full_name='cometbft.services.pruning.v1.SetTxIndexerRetainHeightResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
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
  serialized_start=544,
  serialized_end=578,
)


_GETTXINDEXERRETAINHEIGHTREQUEST = _descriptor.Descriptor(
  name='GetTxIndexerRetainHeightRequest',
  full_name='cometbft.services.pruning.v1.GetTxIndexerRetainHeightRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
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
  serialized_start=580,
  serialized_end=613,
)


_GETTXINDEXERRETAINHEIGHTRESPONSE = _descriptor.Descriptor(
  name='GetTxIndexerRetainHeightResponse',
  full_name='cometbft.services.pruning.v1.GetTxIndexerRetainHeightResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='height', full_name='cometbft.services.pruning.v1.GetTxIndexerRetainHeightResponse.height', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=615,
  serialized_end=665,
)


_SETBLOCKINDEXERRETAINHEIGHTREQUEST = _descriptor.Descriptor(
  name='SetBlockIndexerRetainHeightRequest',
  full_name='cometbft.services.pruning.v1.SetBlockIndexerRetainHeightRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='height', full_name='cometbft.services.pruning.v1.SetBlockIndexerRetainHeightRequest.height', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=667,
  serialized_end=719,
)


_SETBLOCKINDEXERRETAINHEIGHTRESPONSE = _descriptor.Descriptor(
  name='SetBlockIndexerRetainHeightResponse',
  full_name='cometbft.services.pruning.v1.SetBlockIndexerRetainHeightResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
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
  serialized_start=721,
  serialized_end=758,
)


_GETBLOCKINDEXERRETAINHEIGHTREQUEST = _descriptor.Descriptor(
  name='GetBlockIndexerRetainHeightRequest',
  full_name='cometbft.services.pruning.v1.GetBlockIndexerRetainHeightRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
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
  serialized_start=760,
  serialized_end=796,
)


_GETBLOCKINDEXERRETAINHEIGHTRESPONSE = _descriptor.Descriptor(
  name='GetBlockIndexerRetainHeightResponse',
  full_name='cometbft.services.pruning.v1.GetBlockIndexerRetainHeightResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='height', full_name='cometbft.services.pruning.v1.GetBlockIndexerRetainHeightResponse.height', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=798,
  serialized_end=851,
)

DESCRIPTOR.message_types_by_name['SetBlockRetainHeightRequest'] = _SETBLOCKRETAINHEIGHTREQUEST
DESCRIPTOR.message_types_by_name['SetBlockRetainHeightResponse'] = _SETBLOCKRETAINHEIGHTRESPONSE
DESCRIPTOR.message_types_by_name['GetBlockRetainHeightRequest'] = _GETBLOCKRETAINHEIGHTREQUEST
DESCRIPTOR.message_types_by_name['GetBlockRetainHeightResponse'] = _GETBLOCKRETAINHEIGHTRESPONSE
DESCRIPTOR.message_types_by_name['SetBlockResultsRetainHeightRequest'] = _SETBLOCKRESULTSRETAINHEIGHTREQUEST
DESCRIPTOR.message_types_by_name['SetBlockResultsRetainHeightResponse'] = _SETBLOCKRESULTSRETAINHEIGHTRESPONSE
DESCRIPTOR.message_types_by_name['GetBlockResultsRetainHeightRequest'] = _GETBLOCKRESULTSRETAINHEIGHTREQUEST
DESCRIPTOR.message_types_by_name['GetBlockResultsRetainHeightResponse'] = _GETBLOCKRESULTSRETAINHEIGHTRESPONSE
DESCRIPTOR.message_types_by_name['SetTxIndexerRetainHeightRequest'] = _SETTXINDEXERRETAINHEIGHTREQUEST
DESCRIPTOR.message_types_by_name['SetTxIndexerRetainHeightResponse'] = _SETTXINDEXERRETAINHEIGHTRESPONSE
DESCRIPTOR.message_types_by_name['GetTxIndexerRetainHeightRequest'] = _GETTXINDEXERRETAINHEIGHTREQUEST
DESCRIPTOR.message_types_by_name['GetTxIndexerRetainHeightResponse'] = _GETTXINDEXERRETAINHEIGHTRESPONSE
DESCRIPTOR.message_types_by_name['SetBlockIndexerRetainHeightRequest'] = _SETBLOCKINDEXERRETAINHEIGHTREQUEST
DESCRIPTOR.message_types_by_name['SetBlockIndexerRetainHeightResponse'] = _SETBLOCKINDEXERRETAINHEIGHTRESPONSE
DESCRIPTOR.message_types_by_name['GetBlockIndexerRetainHeightRequest'] = _GETBLOCKINDEXERRETAINHEIGHTREQUEST
DESCRIPTOR.message_types_by_name['GetBlockIndexerRetainHeightResponse'] = _GETBLOCKINDEXERRETAINHEIGHTRESPONSE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

SetBlockRetainHeightRequest = _reflection.GeneratedProtocolMessageType('SetBlockRetainHeightRequest', (_message.Message,), {
  'DESCRIPTOR' : _SETBLOCKRETAINHEIGHTREQUEST,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.SetBlockRetainHeightRequest)
  })
_sym_db.RegisterMessage(SetBlockRetainHeightRequest)

SetBlockRetainHeightResponse = _reflection.GeneratedProtocolMessageType('SetBlockRetainHeightResponse', (_message.Message,), {
  'DESCRIPTOR' : _SETBLOCKRETAINHEIGHTRESPONSE,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.SetBlockRetainHeightResponse)
  })
_sym_db.RegisterMessage(SetBlockRetainHeightResponse)

GetBlockRetainHeightRequest = _reflection.GeneratedProtocolMessageType('GetBlockRetainHeightRequest', (_message.Message,), {
  'DESCRIPTOR' : _GETBLOCKRETAINHEIGHTREQUEST,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.GetBlockRetainHeightRequest)
  })
_sym_db.RegisterMessage(GetBlockRetainHeightRequest)

GetBlockRetainHeightResponse = _reflection.GeneratedProtocolMessageType('GetBlockRetainHeightResponse', (_message.Message,), {
  'DESCRIPTOR' : _GETBLOCKRETAINHEIGHTRESPONSE,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.GetBlockRetainHeightResponse)
  })
_sym_db.RegisterMessage(GetBlockRetainHeightResponse)

SetBlockResultsRetainHeightRequest = _reflection.GeneratedProtocolMessageType('SetBlockResultsRetainHeightRequest', (_message.Message,), {
  'DESCRIPTOR' : _SETBLOCKRESULTSRETAINHEIGHTREQUEST,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.SetBlockResultsRetainHeightRequest)
  })
_sym_db.RegisterMessage(SetBlockResultsRetainHeightRequest)

SetBlockResultsRetainHeightResponse = _reflection.GeneratedProtocolMessageType('SetBlockResultsRetainHeightResponse', (_message.Message,), {
  'DESCRIPTOR' : _SETBLOCKRESULTSRETAINHEIGHTRESPONSE,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.SetBlockResultsRetainHeightResponse)
  })
_sym_db.RegisterMessage(SetBlockResultsRetainHeightResponse)

GetBlockResultsRetainHeightRequest = _reflection.GeneratedProtocolMessageType('GetBlockResultsRetainHeightRequest', (_message.Message,), {
  'DESCRIPTOR' : _GETBLOCKRESULTSRETAINHEIGHTREQUEST,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.GetBlockResultsRetainHeightRequest)
  })
_sym_db.RegisterMessage(GetBlockResultsRetainHeightRequest)

GetBlockResultsRetainHeightResponse = _reflection.GeneratedProtocolMessageType('GetBlockResultsRetainHeightResponse', (_message.Message,), {
  'DESCRIPTOR' : _GETBLOCKRESULTSRETAINHEIGHTRESPONSE,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.GetBlockResultsRetainHeightResponse)
  })
_sym_db.RegisterMessage(GetBlockResultsRetainHeightResponse)

SetTxIndexerRetainHeightRequest = _reflection.GeneratedProtocolMessageType('SetTxIndexerRetainHeightRequest', (_message.Message,), {
  'DESCRIPTOR' : _SETTXINDEXERRETAINHEIGHTREQUEST,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.SetTxIndexerRetainHeightRequest)
  })
_sym_db.RegisterMessage(SetTxIndexerRetainHeightRequest)

SetTxIndexerRetainHeightResponse = _reflection.GeneratedProtocolMessageType('SetTxIndexerRetainHeightResponse', (_message.Message,), {
  'DESCRIPTOR' : _SETTXINDEXERRETAINHEIGHTRESPONSE,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.SetTxIndexerRetainHeightResponse)
  })
_sym_db.RegisterMessage(SetTxIndexerRetainHeightResponse)

GetTxIndexerRetainHeightRequest = _reflection.GeneratedProtocolMessageType('GetTxIndexerRetainHeightRequest', (_message.Message,), {
  'DESCRIPTOR' : _GETTXINDEXERRETAINHEIGHTREQUEST,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.GetTxIndexerRetainHeightRequest)
  })
_sym_db.RegisterMessage(GetTxIndexerRetainHeightRequest)

GetTxIndexerRetainHeightResponse = _reflection.GeneratedProtocolMessageType('GetTxIndexerRetainHeightResponse', (_message.Message,), {
  'DESCRIPTOR' : _GETTXINDEXERRETAINHEIGHTRESPONSE,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.GetTxIndexerRetainHeightResponse)
  })
_sym_db.RegisterMessage(GetTxIndexerRetainHeightResponse)

SetBlockIndexerRetainHeightRequest = _reflection.GeneratedProtocolMessageType('SetBlockIndexerRetainHeightRequest', (_message.Message,), {
  'DESCRIPTOR' : _SETBLOCKINDEXERRETAINHEIGHTREQUEST,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.SetBlockIndexerRetainHeightRequest)
  })
_sym_db.RegisterMessage(SetBlockIndexerRetainHeightRequest)

SetBlockIndexerRetainHeightResponse = _reflection.GeneratedProtocolMessageType('SetBlockIndexerRetainHeightResponse', (_message.Message,), {
  'DESCRIPTOR' : _SETBLOCKINDEXERRETAINHEIGHTRESPONSE,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.SetBlockIndexerRetainHeightResponse)
  })
_sym_db.RegisterMessage(SetBlockIndexerRetainHeightResponse)

GetBlockIndexerRetainHeightRequest = _reflection.GeneratedProtocolMessageType('GetBlockIndexerRetainHeightRequest', (_message.Message,), {
  'DESCRIPTOR' : _GETBLOCKINDEXERRETAINHEIGHTREQUEST,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.GetBlockIndexerRetainHeightRequest)
  })
_sym_db.RegisterMessage(GetBlockIndexerRetainHeightRequest)

GetBlockIndexerRetainHeightResponse = _reflection.GeneratedProtocolMessageType('GetBlockIndexerRetainHeightResponse', (_message.Message,), {
  'DESCRIPTOR' : _GETBLOCKINDEXERRETAINHEIGHTRESPONSE,
  '__module__' : 'cometbft.services.pruning.v1.pruning_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.services.pruning.v1.GetBlockIndexerRetainHeightResponse)
  })
_sym_db.RegisterMessage(GetBlockIndexerRetainHeightResponse)


# @@protoc_insertion_point(module_scope)
