# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: cometbft/rpc/grpc/v1beta1/types.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from cometbft.abci.v1beta1 import types_pb2 as cometbft_dot_abci_dot_v1beta1_dot_types__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='cometbft/rpc/grpc/v1beta1/types.proto',
  package='cometbft.rpc.grpc.v1beta1',
  syntax='proto3',
  serialized_options=b'Z:github.com/cometbft/cometbft/api/cometbft/rpc/grpc/v1beta1',
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n%cometbft/rpc/grpc/v1beta1/types.proto\x12\x19\x63ometbft.rpc.grpc.v1beta1\x1a!cometbft/abci/v1beta1/types.proto\"\r\n\x0bRequestPing\" \n\x12RequestBroadcastTx\x12\n\n\x02tx\x18\x01 \x01(\x0c\"\x0e\n\x0cResponsePing\"\x8d\x01\n\x13ResponseBroadcastTx\x12\x38\n\x08\x63heck_tx\x18\x01 \x01(\x0b\x32&.cometbft.abci.v1beta1.ResponseCheckTx\x12<\n\ndeliver_tx\x18\x02 \x01(\x0b\x32(.cometbft.abci.v1beta1.ResponseDeliverTx2\xd5\x01\n\x0c\x42roadcastAPI\x12W\n\x04Ping\x12&.cometbft.rpc.grpc.v1beta1.RequestPing\x1a\'.cometbft.rpc.grpc.v1beta1.ResponsePing\x12l\n\x0b\x42roadcastTx\x12-.cometbft.rpc.grpc.v1beta1.RequestBroadcastTx\x1a..cometbft.rpc.grpc.v1beta1.ResponseBroadcastTxB<Z:github.com/cometbft/cometbft/api/cometbft/rpc/grpc/v1beta1b\x06proto3'
  ,
  dependencies=[cometbft_dot_abci_dot_v1beta1_dot_types__pb2.DESCRIPTOR,])




_REQUESTPING = _descriptor.Descriptor(
  name='RequestPing',
  full_name='cometbft.rpc.grpc.v1beta1.RequestPing',
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
  serialized_start=103,
  serialized_end=116,
)


_REQUESTBROADCASTTX = _descriptor.Descriptor(
  name='RequestBroadcastTx',
  full_name='cometbft.rpc.grpc.v1beta1.RequestBroadcastTx',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='tx', full_name='cometbft.rpc.grpc.v1beta1.RequestBroadcastTx.tx', index=0,
      number=1, type=12, cpp_type=9, label=1,
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
  serialized_start=118,
  serialized_end=150,
)


_RESPONSEPING = _descriptor.Descriptor(
  name='ResponsePing',
  full_name='cometbft.rpc.grpc.v1beta1.ResponsePing',
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
  serialized_start=152,
  serialized_end=166,
)


_RESPONSEBROADCASTTX = _descriptor.Descriptor(
  name='ResponseBroadcastTx',
  full_name='cometbft.rpc.grpc.v1beta1.ResponseBroadcastTx',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='check_tx', full_name='cometbft.rpc.grpc.v1beta1.ResponseBroadcastTx.check_tx', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='deliver_tx', full_name='cometbft.rpc.grpc.v1beta1.ResponseBroadcastTx.deliver_tx', index=1,
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
  serialized_start=169,
  serialized_end=310,
)

_RESPONSEBROADCASTTX.fields_by_name['check_tx'].message_type = cometbft_dot_abci_dot_v1beta1_dot_types__pb2._RESPONSECHECKTX
_RESPONSEBROADCASTTX.fields_by_name['deliver_tx'].message_type = cometbft_dot_abci_dot_v1beta1_dot_types__pb2._RESPONSEDELIVERTX
DESCRIPTOR.message_types_by_name['RequestPing'] = _REQUESTPING
DESCRIPTOR.message_types_by_name['RequestBroadcastTx'] = _REQUESTBROADCASTTX
DESCRIPTOR.message_types_by_name['ResponsePing'] = _RESPONSEPING
DESCRIPTOR.message_types_by_name['ResponseBroadcastTx'] = _RESPONSEBROADCASTTX
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

RequestPing = _reflection.GeneratedProtocolMessageType('RequestPing', (_message.Message,), {
  'DESCRIPTOR' : _REQUESTPING,
  '__module__' : 'cometbft.rpc.grpc.v1beta1.types_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.rpc.grpc.v1beta1.RequestPing)
  })
_sym_db.RegisterMessage(RequestPing)

RequestBroadcastTx = _reflection.GeneratedProtocolMessageType('RequestBroadcastTx', (_message.Message,), {
  'DESCRIPTOR' : _REQUESTBROADCASTTX,
  '__module__' : 'cometbft.rpc.grpc.v1beta1.types_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.rpc.grpc.v1beta1.RequestBroadcastTx)
  })
_sym_db.RegisterMessage(RequestBroadcastTx)

ResponsePing = _reflection.GeneratedProtocolMessageType('ResponsePing', (_message.Message,), {
  'DESCRIPTOR' : _RESPONSEPING,
  '__module__' : 'cometbft.rpc.grpc.v1beta1.types_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.rpc.grpc.v1beta1.ResponsePing)
  })
_sym_db.RegisterMessage(ResponsePing)

ResponseBroadcastTx = _reflection.GeneratedProtocolMessageType('ResponseBroadcastTx', (_message.Message,), {
  'DESCRIPTOR' : _RESPONSEBROADCASTTX,
  '__module__' : 'cometbft.rpc.grpc.v1beta1.types_pb2'
  # @@protoc_insertion_point(class_scope:cometbft.rpc.grpc.v1beta1.ResponseBroadcastTx)
  })
_sym_db.RegisterMessage(ResponseBroadcastTx)


DESCRIPTOR._options = None

_BROADCASTAPI = _descriptor.ServiceDescriptor(
  name='BroadcastAPI',
  full_name='cometbft.rpc.grpc.v1beta1.BroadcastAPI',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=313,
  serialized_end=526,
  methods=[
  _descriptor.MethodDescriptor(
    name='Ping',
    full_name='cometbft.rpc.grpc.v1beta1.BroadcastAPI.Ping',
    index=0,
    containing_service=None,
    input_type=_REQUESTPING,
    output_type=_RESPONSEPING,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='BroadcastTx',
    full_name='cometbft.rpc.grpc.v1beta1.BroadcastAPI.BroadcastTx',
    index=1,
    containing_service=None,
    input_type=_REQUESTBROADCASTTX,
    output_type=_RESPONSEBROADCASTTX,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_BROADCASTAPI)

DESCRIPTOR.services_by_name['BroadcastAPI'] = _BROADCASTAPI

# @@protoc_insertion_point(module_scope)
