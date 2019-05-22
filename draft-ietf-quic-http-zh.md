---
title: Hypertext Transfer Protocol Version 3 (HTTP/3)
abbrev: HTTP/3
docname: draft-ietf-quic-http-latest
date: {DATE}
category: std
ipr: trust200902
area: Transport
workgroup: QUIC

stand_alone: yes
pi: [toc, sortrefs, symrefs, docmapping]

author:
-
    ins: M. Bishop
    name: Mike Bishop
    org: Akamai
    email: mbishop@evequefou.be
    role: editor

normative:

  QUIC-TRANSPORT:
    title: "QUIC: A UDP-Based Multiplexed and Secure Transport"
    date: {DATE}
    seriesinfo:
      Internet-Draft: draft-ietf-quic-transport-latest
    author:
      -
        ins: J. Iyengar
        name: Jana Iyengar
        org: Fastly
        role: editor
      -
        ins: M. Thomson
        name: Martin Thomson
        org: Mozilla
        role: editor

  QPACK:
    title: "QPACK: Header Compression for HTTP over QUIC"
    date: {DATE}
    seriesinfo:
      Internet-Draft: draft-ietf-quic-qpack-latest
    author:
      -
          ins: C. Krasic
          name: Charles 'Buck' Krasic
          org: Google, Inc
      -
          ins: M. Bishop
          name: Mike Bishop
          org: Akamai Technologies
      -
          ins: A. Frindell
          name: Alan Frindell
          org: Facebook
          role: editor


informative:


--- abstract

The QUIC transport protocol has several features that are desirable in a
transport for HTTP, such as stream multiplexing, per-stream flow control, and
low-latency connection establishment.  This document describes a mapping of HTTP
semantics over QUIC.  This document also identifies HTTP/2 features that are
subsumed by QUIC, and describes how HTTP/2 extensions can be ported to HTTP/3.

--- note_Note_to_Readers

Discussion of this draft takes place on the QUIC working group mailing list
(quic@ietf.org), which is archived at
<https://mailarchive.ietf.org/arch/search/?email_list=quic>.

Working Group information can be found at <https://github.com/quicwg>; source
code and issues list for this draft can be found at
<https://github.com/quicwg/base-drafts/labels/-http>.


--- middle


# 简介(Introduction)

HTTP 语义用于互联网上的广泛服务。这些语义一般用于两不同端的TCP映射，HTTP/1.1以及HTTP/2。
HTTp/2 引入了帧和多路复用来不修改传输层的改善延迟。
然而，TCP在两端映射中对并行请求的可见性的缺失限制了性能提高的可能空间。

QUIC 传输协议包含了类似于HTTP/2在成帧层提供的流多路复用与基于流的流量控制。
提供在流级别可靠性和对整个连接的拥塞控制，与HTTP映射相比，提高HTTP性能有了空间。
QUIC 在传输层同样包含了 TLS 1.3，在提供了类似于在TCP上的运行TLS的安全性的前提下，
提高了连接建立阶段的延迟(除非开启了TCP快速打开{{?RFC7413}})。

这篇文档定义了HTTP语义在QUIC传输协议上的映射，在很大程度上依赖了HTTP/2的设计。
这篇文档标识了QUIC拥有的HTTP/2特性，并且描述了其他可在QUIC上实现的特性。

QUIC 描述于{{QUIC-TRANSPORT}}。
关于完整的HTTP/2的描述，详见{{!RFC7540}}。


## 通用术语(Notational Conventions)

关键词“必须(MUST)”，“禁止(MUST NOT)”，“必需(REQUIRED)”，“应当(SHALL)”，
“应当不(SHALL NOT)”，“应该(SHOULD)”，“不应该(SHOULD NOT)”，“推荐(RECOMMENDED)”，
“不推荐(NOT RECOMMENDED)”，“可以(MAY)”，“可选(OPTIONAL)”
在这篇文档中将会如 BCP 14{{!RFC2119}} {{!RFC8174}}中描述的，当且仅当他们如此例子显示的以加粗的形式出现时。
文档中常用的术语在下方描述。

字段描述以扩展的巴科斯范式(Augmented Backus-Naur Form 即ABNF)给出，定义在{{!RFC5234}}中。

这篇文档使用了{{QUIC-TRANSPORT}}中的变长的整数编码。

称呼为"帧"的协议元素存在于本文档和{{QUIC-TRANSPORT}}。
当引用的帧是{{QUIC-TRANSPORT}}中的，帧名字会以"QUIC"打头。
例如"QUIC CONNECTION_CLOSE 帧"。
不以这个开头的引用的帧定义于{{frames}}。


# Connection Setup and Management

## Draft Version Identification

> **RFC Editor's Note:**  Please remove this section prior to publication of a
> final version of this document.

HTTP/3 uses the token "h3" to identify itself in ALPN and Alt-Svc.  Only
implementations of the final, published RFC can identify themselves as "h3".
Until such an RFC exists, implementations MUST NOT identify themselves using
this string.

Implementations of draft versions of the protocol MUST add the string "-" and
the corresponding draft number to the identifier. For example,
draft-ietf-quic-http-01 is identified using the string "h3-01".

Non-compatible experiments that are based on these draft versions MUST append
the string "-" and an experiment name to the identifier. For example, an
experimental implementation based on draft-ietf-quic-http-09 which reserves an
extra stream for unsolicited transmission of 1980s pop music might identify
itself as "h3-09-rickroll". Note that any label MUST conform to the "token"
syntax defined in Section 3.2.6 of [RFC7230]. Experimenters are encouraged to
coordinate their experiments on the quic@ietf.org mailing list.

## Discovering an HTTP/3 Endpoint

An HTTP origin advertises the availability of an equivalent HTTP/3 endpoint via
the Alt-Svc HTTP response header field or the HTTP/2 ALTSVC frame
({{!ALTSVC=RFC7838}}), using the ALPN token defined in
{{connection-establishment}}.

For example, an origin could indicate in an HTTP response that HTTP/3 was
available on UDP port 50781 at the same hostname by including the following
header field:

~~~ example
Alt-Svc: h3=":50781"
~~~

On receipt of an Alt-Svc record indicating HTTP/3 support, a client MAY attempt
to establish a QUIC connection to the indicated host and port and, if
successful, send HTTP requests using the mapping described in this document.

Connectivity problems (e.g. firewall blocking UDP) can result in QUIC connection
establishment failure, in which case the client SHOULD continue using the
existing connection or try another alternative endpoint offered by the origin.

Servers MAY serve HTTP/3 on any UDP port, since an alternative always includes
an explicit port.

### QUIC Version Hints {#alt-svc-version-hint}

This document defines the "quic" parameter for Alt-Svc, which MAY be used to
provide version-negotiation hints to HTTP/3 clients. QUIC versions are four-byte
sequences with no additional constraints on format. Leading zeros SHOULD be
omitted for brevity.

Syntax:

~~~ abnf
quic = DQUOTE version-number [ "," version-number ] * DQUOTE
version-number = 1*8HEXDIG; hex-encoded QUIC version
~~~

Where multiple versions are listed, the order of the values reflects the
server's preference (with the first value being the most preferred version).
Reserved versions MAY be listed, but unreserved versions which are not supported
by the alternative SHOULD NOT be present in the list. Origins MAY omit supported
versions for any reason.

Clients MUST ignore any included versions which they do not support.  The "quic"
parameter MUST NOT occur more than once; clients SHOULD process only the first
occurrence.

For example, suppose a server supported both version 0x00000001 and the version
rendered in ASCII as "Q034".  If it also opted to include the reserved version
(from Section 15 of {{QUIC-TRANSPORT}}) 0x1abadaba, it could specify the
following header field:

~~~ example
Alt-Svc: h3=":49288";quic="1,1abadaba,51303334"
~~~

A client acting on this header field would drop the reserved version (not
supported), then attempt to connect to the alternative using the first version
in the list which it does support, if any.

## Connection Establishment {#connection-establishment}

HTTP/3 relies on QUIC as the underlying transport.  The QUIC version being used
MUST use TLS version 1.3 or greater as its handshake protocol.  HTTP/3 clients
MUST indicate the target domain name during the TLS handshake. This may be done
using the Server Name Indication (SNI) {{!RFC6066}} extension to TLS or using
some other mechanism.

QUIC connections are established as described in {{QUIC-TRANSPORT}}. During
connection establishment, HTTP/3 support is indicated by selecting the ALPN
token "h3" in the TLS handshake.  Support for other application-layer protocols
MAY be offered in the same handshake.

While connection-level options pertaining to the core QUIC protocol are set in
the initial crypto handshake, HTTP/3-specific settings are conveyed in the
SETTINGS frame. After the QUIC connection is established, a SETTINGS frame
({{frame-settings}}) MUST be sent by each endpoint as the initial frame of their
respective HTTP control stream (see {{control-streams}}).

## Connection Reuse

Once a connection exists to a server endpoint, this connection MAY be reused for
requests with multiple different URI authority components.  The client MAY send
any requests for which the client considers the server authoritative.

An authoritative HTTP/3 endpoint is typically discovered because the client has
received an Alt-Svc record from the request's origin which nominates the
endpoint as a valid HTTP Alternative Service for that origin.  As required by
{{RFC7838}}, clients MUST check that the nominated server can present a valid
certificate for the origin before considering it authoritative. Clients MUST NOT
assume that an HTTP/3 endpoint is authoritative for other origins without an
explicit signal.

A server that does not wish clients to reuse connections for a particular origin
can indicate that it is not authoritative for a request by sending a 421
(Misdirected Request) status code in response to the request (see Section 9.1.2
of {{!RFC7540}}).

The considerations discussed in Section 9.1 of {{?RFC7540}} also apply to the
management of HTTP/3 connections.

# Stream Mapping and Usage {#stream-mapping}

A QUIC stream provides reliable in-order delivery of bytes, but makes no
guarantees about order of delivery with regard to bytes on other streams. On the
wire, data is framed into QUIC STREAM frames, but this framing is invisible to
the HTTP framing layer. The transport layer buffers and orders received QUIC
STREAM frames, exposing the data contained within as a reliable byte stream to
the application. Although QUIC permits out-of-order delivery within a stream
HTTP/3 does not make use of this feature.

QUIC streams can be either unidirectional, carrying data only from initiator to
receiver, or bidirectional.  Streams can be initiated by either the client or
the server.  For more detail on QUIC streams, see Section 2 of
{{QUIC-TRANSPORT}}.

When HTTP headers and data are sent over QUIC, the QUIC layer handles most of
the stream management.  HTTP does not need to do any separate multiplexing when
using QUIC - data sent over a QUIC stream always maps to a particular HTTP
transaction or connection context.

## Bidirectional Streams

All client-initiated bidirectional streams are used for HTTP requests and
responses.  A bidirectional stream ensures that the response can be readily
correlated with the request. This means that the client's first request occurs
on QUIC stream 0, with subsequent requests on stream 4, 8, and so on. In order
to permit these streams to open, an HTTP/3 client SHOULD send non-zero values
for the QUIC transport parameters `initial_max_stream_data_bidi_local`. An
HTTP/3 server SHOULD send non-zero values for the QUIC transport parameters
`initial_max_stream_data_bidi_remote` and `initial_max_bidi_streams`. It is
recommended that `initial_max_bidi_streams` be no smaller than 100, so as to not
unnecessarily limit parallelism.

These streams carry frames related to the request/response (see
{{request-response}}). When a stream terminates cleanly, if the last frame on
the stream was truncated, this MUST be treated as a connection error (see
HTTP_MALFORMED_FRAME in {{http-error-codes}}).  Streams which terminate abruptly
may be reset at any point in the frame.

HTTP/3 does not use server-initiated bidirectional streams; clients MUST omit or
specify a value of zero for the QUIC transport parameter
`initial_max_bidi_streams`.


## Unidirectional Streams

Unidirectional streams, in either direction, are used for a range of purposes.
The purpose is indicated by a stream type, which is sent as a variable-length
integer at the start of the stream. The format and structure of data that
follows this integer is determined by the stream type.

~~~~~~~~~~ drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Stream Type (i)                      ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-stream-header title="Unidirectional Stream Header"}

Some stream types are reserved ({{stream-grease}}).  Two stream types are
defined in this document: control streams ({{control-streams}}) and push streams
({{push-streams}}).  Other stream types can be defined by extensions to HTTP/3;
see {{extensions}} for more details.

Both clients and servers SHOULD send a value of three or greater for the QUIC
transport parameter `initial_max_uni_streams`.

If the stream header indicates a stream type which is not supported by the
recipient, the remainder of the stream cannot be consumed as the semantics are
unknown. Recipients of unknown stream types MAY trigger a QUIC STOP_SENDING
frame with an error code of HTTP_UNKNOWN_STREAM_TYPE, but MUST NOT consider such
streams to be an error of any kind.

Implementations MAY send stream types before knowing whether the peer supports
them.  However, stream types which could modify the state or semantics of
existing protocol components, including QPACK or other extensions, MUST NOT be
sent until the peer is known to support them.

A sender can close or reset a unidirectional stream unless otherwise specified.
A receiver MUST tolerate unidirectional streams being closed or reset prior to
the reception of the unidirectional stream header.

###  Control Streams

A control stream is indicated by a stream type of `0x00`.  Data on this stream
consists of HTTP/3 frames, as defined in {{frames}}.

Each side MUST initiate a single control stream at the beginning of the
connection and send its SETTINGS frame as the first frame on this stream.  If
the first frame of the control stream is any other frame type, this MUST be
treated as a connection error of type HTTP_MISSING_SETTINGS. Only one control
stream per peer is permitted; receipt of a second stream which claims to be a
control stream MUST be treated as a connection error of type
HTTP_WRONG_STREAM_COUNT.  The sender MUST NOT close the control stream.  If the
control stream is closed at any point, this MUST be treated as a connection
error of type HTTP_CLOSED_CRITICAL_STREAM.

A pair of unidirectional streams is used rather than a single bidirectional
stream.  This allows either peer to send data as soon they are able.  Depending
on whether 0-RTT is enabled on the connection, either client or server might be
able to send stream data first after the cryptographic handshake completes.

### Push Streams

A push stream is indicated by a stream type of `0x01`, followed by the Push ID
of the promise that it fulfills, encoded as a variable-length integer. The
remaining data on this stream consists of HTTP/3 frames, as defined in
{{frames}}, and fulfills a promised server push.  Server push and Push IDs are
described in {{server-push}}.

Only servers can push; if a server receives a client-initiated push stream, this
MUST be treated as a stream error of type HTTP_WRONG_STREAM_DIRECTION.

~~~~~~~~~~ drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           0x01 (i)                          ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Push ID (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-push-stream-header title="Push Stream Header"}

Each Push ID MUST only be used once in a push stream header. If a push stream
header includes a Push ID that was used in another push stream header, the
client MUST treat this as a connection error of type HTTP_DUPLICATE_PUSH.

### Reserved Stream Types {#stream-grease}

Stream types of the format `0x1f * N + 0x21` for integer values of N are
reserved to exercise the requirement that unknown types be ignored. These
streams have no semantics, and can be sent when application-layer padding is
desired. They MAY also be sent on connections where no data is currently being
transferred. Endpoints MUST NOT consider these streams to have any meaning upon
receipt.

The payload and length of the stream are selected in any manner the
implementation chooses.


# HTTP Framing Layer {#http-framing-layer}

HTTP frames are carried on QUIC streams, as described in {{stream-mapping}}.
HTTP/3 defines three stream types: control stream, request stream, and push
stream. This section describes HTTP/3 frame formats and the streams types on
which they are permitted; see {{stream-frame-mapping}} for an overiew.  A
comparison between HTTP/2 and HTTP/3 frames is provided in {{h2-frames}}.

| Frame          | Control Stream | Request Stream | Push Stream | Section                  |
| -------------- | -------------- | -------------- | ----------- | ------------------------ |
| DATA           | No             | Yes            | Yes         | {{frame-data}}           |
| HEADERS        | No             | Yes            | Yes         | {{frame-headers}}        |
| PRIORITY       | Yes            | Yes (1)        | No          | {{frame-priority}}       |
| CANCEL_PUSH    | Yes            | No             | No          | {{frame-cancel-push}}    |
| SETTINGS       | Yes (1)        | No             | No          | {{frame-settings}}       |
| PUSH_PROMISE   | No             | Yes            | No          | {{frame-push-promise}}   |
| GOAWAY         | Yes            | No             | No          | {{frame-goaway}}         |
| MAX_PUSH_ID    | Yes            | No             | No          | {{frame-max-push-id}}    |
| DUPLICATE_PUSH | No             | Yes            | No          | {{frame-duplicate-push}} |
{: #stream-frame-mapping title="HTTP/3 frames and stream type overview"}

Certain frames can only occur as the first frame of a particular stream type;
these are indicated in {{stream-frame-mapping}} with a (1).  Specific guidance
is provided in the relevant section.

## Frame Layout

All frames have the following format:

~~~~~~~~~~ drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           Type (i)                          ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Length (i)                         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Frame Payload (*)                     ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-frame title="HTTP/3 frame format"}

A frame includes the following fields:

  Type:
  : A variable-length integer that identifies the frame type.

  Length:
  : A variable-length integer that describes the length of the Frame Payload.

  Frame Payload:
  : A payload, the semantics of which are determined by the Type field.

Each frame's payload MUST contain exactly the fields identified in its
description.  A frame payload that contains additional bytes after the
identified fields or a frame payload that terminates before the end of the
identified fields MUST be treated as a connection error of type
HTTP_MALFORMED_FRAME.

## Frame Definitions {#frames}

### DATA {#frame-data}

DATA frames (type=0x0) convey arbitrary, variable-length sequences of bytes
associated with an HTTP request or response payload.

DATA frames MUST be associated with an HTTP request or response.  If a DATA
frame is received on either control stream, the recipient MUST respond with a
connection error ({{errors}}) of type HTTP_WRONG_STREAM.

~~~~~~~~~~ drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Payload (*)                         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-data title="DATA frame payload"}

### HEADERS {#frame-headers}

The HEADERS frame (type=0x1) is used to carry a header block, compressed using
QPACK. See [QPACK] for more details.

~~~~~~~~~~  drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Header Block (*)                      ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-headers title="HEADERS frame payload"}

HEADERS frames can only be sent on request / push streams.

### 优先级帧(PRIORITY) {#frame-priority}


PRIORITY帧(类型=0x02)指定请求、服务器推送或占位符的客户端建议的优先级。

PRIORITY帧标识要优先排序的元素以及它所依赖的元素。优先级ID或依赖ID使用
相应的流ID标识客户端发起的请求，使用推送ID标识服务器推送(请参见
{{frame-push-promise}})，或使用占位符ID标识占位符(请参见{{placeholders}})。

当客户端发起请求时，**可以**将PRIORITY帧作为流的第一帧发送，从而创建对现有
元素的依赖。为了确保以一致的顺序处理优先级，该请求的任何后续PRIORITY帧都
**必须**在控制流上发送。在请求流上的其他帧之后接收到的PRIORITY帧**必须**被视为
HTTP_UNEXPECTED_FRAME类型的流错误。

如果在打开新的请求流时，已通过控制流接收到其优先级信息，则必须忽略在请求
流上发送的PRIORITY帧。

~~~~~~~~~~  drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|PT |DT | 空 |               [优先级元素ID(i)]             ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         [元素依赖ID(i)]                     ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  权重 (8)  |
+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-priority title="PRIORITY frame payload"}

PRIORITY帧有效负载具有以下字段：

  PT (优先元素类型):
  : 一个两位字段，指示被优先处理的元素的类型(参见
    {{prioritized-element-types}}). 在请求流中发送时，
    **必须**将其设置为`11`。在控制流上发送时，**禁止**将其设置为`11`。

  DT (元素依赖类型):
  : 指示所依赖的元素类型的两位字段(参见
    {{element-dependency-types}})。

  空:
  : 发送时**必须**为零且在收到时**必须**忽略的四位字段。

  优先元素ID:
  : 标识要优先处理的元素的可变长度整数。根据优先类型的值，它包含请求流的流ID、
  承诺资源的推送ID、占位符的占位符ID或缺失。

  元素依赖ID:
  : 一个可变长度整数，用于标识表示依赖项的元素。根据依赖类型的值，它包含请求流的
  流ID、承诺资源的推送ID、占位符的占位符ID或缺失。有关依赖项的详细信息，请参见
  {{priority}}和{{!RFC7540}}, 第5.3节.

  权重:
  : 一个无符号8位整数，表示优先元素的优先权重(参见 {{!RFC7540}},第5.3节)。 
  向值中添加一个以获得介于1和256之间的权重。

优先元素类型({{prioritized-element-types}})和元素依赖类型({{element-dependency-types}})
的值隐含着关联元素ID字段的解释。

| PT 位 | 类型描述 | 优先元素ID内容 |
| ------- | ---------------- | ------------------------------- |
| 00      | 请求流  | 流ID                      |
| 01      | 推送流      | 推送ID                       |
| 10      | 占位符      | 占位符ID                 |
| 11      | 当前流   | 缺失                         |
{: #prioritized-element-types title="Prioritized Element Types"}

| DT 位   | 类型描述 | 元素依赖ID内容 |
| ------- | ---------------- | ------------------------------ |
| 00      | 请求流   | 流ID                    |
| 01      | 推送流     | 推送ID                   |
| 10      | 占位符      | 占位符ID                |
| 11      | 树的根节点 | 缺失                         |
{: #element-dependency-types title="Element Dependency Types"}

请注意，与{{!RFC7540}}不同，不能使用为0的流ID引用树的根节点，因为
QUIC流0包含有效的HTTP请求。树的根节点不能被重新排序。在优先级元素类型
设置为“11”以外的任何值的请求流上发送的PRIORITY帧，或者在具有大于当前流的
流ID的请求流上表达依赖关系的PRIORITY帧**必须**被视为HTTP_MALFORMED_FRAME
类型的流错误。必须将当前流视为类型为HTTP_MERFORM_FRAME的流错误。
同样，在优先级元素类型设置为`11`的控制流上发送的优先级帧**必须**被视
为HTTP_MALFORMED_FRAME类型的连接错误。

当PRIORITY帧声称引用请求时，关联的ID**必须**标识客户端启动的双向流。
服务器**必须**将接收到标识任何其他类型的流的PRIORITY帧视为类型为
HTTP_MALFORMED_FRAME的连接错误。

引用不存在的推送ID、超过服务器限制的占位符ID或客户端尚不允许打开
的流ID的PRIORITY帧**必须**视为HTTP_LIMIT_EXCEEDED错误。

在请求或控制流以外的任何流上接收到的PRIORITY帧**必须**被视为类型为
HTTP_WRONG_STREAM的连接错误。

客户端接收到的PRIORITY帧**必须**被视为HTTP_UNEXPECTED_FRAME类型
的流错误。 

### CANCEL_PUSH {#frame-cancel-push}

The CANCEL_PUSH frame (type=0x3) is used to request cancellation of a server
push prior to the push stream being received.  The CANCEL_PUSH frame identifies
a server push by Push ID (see {{frame-push-promise}}), encoded as a
variable-length integer.

When a server receives this frame, it aborts sending the response for the
identified server push.  If the server has not yet started to send the server
push, it can use the receipt of a CANCEL_PUSH frame to avoid opening a push
stream.  If the push stream has been opened by the server, the server SHOULD
send a QUIC RESET_STREAM frame on that stream and cease transmission of the
response.

A server can send the CANCEL_PUSH frame to indicate that it will not be
fulfilling a promise prior to creation of a push stream.  Once the push stream
has been created, sending CANCEL_PUSH has no effect on the state of the push
stream.  A QUIC RESET_STREAM frame SHOULD be used instead to abort transmission
of the server push response.

A CANCEL_PUSH frame is sent on the control stream.  Receiving a CANCEL_PUSH
frame on a stream other than the control stream MUST be treated as a stream
error of type HTTP_WRONG_STREAM.

~~~~~~~~~~  drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Push ID (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-cancel-push title="CANCEL_PUSH frame payload"}

The CANCEL_PUSH frame carries a Push ID encoded as a variable-length integer.
The Push ID identifies the server push that is being cancelled (see
{{frame-push-promise}}).

If the client receives a CANCEL_PUSH frame, that frame might identify a Push ID
that has not yet been mentioned by a PUSH_PROMISE frame.


### SETTINGS {#frame-settings}

The SETTINGS frame (type=0x4) conveys configuration parameters that affect how
endpoints communicate, such as preferences and constraints on peer behavior.
Individually, a SETTINGS parameter can also be referred to as a "setting"; the
identifier and value of each setting parameter can be referred to as a "setting
identifier" and a "setting value".

SETTINGS frames always apply to a connection, never a single stream.  A SETTINGS
frame MUST be sent as the first frame of each control stream (see
{{control-streams}}) by each peer, and MUST NOT be sent subsequently or on any
other stream. If an endpoint receives a SETTINGS frame on a different stream,
the endpoint MUST respond with a connection error of type HTTP_WRONG_STREAM. If
an endpoint receives a second SETTINGS frame, the endpoint MUST respond with a
connection error of type HTTP_UNEXPECTED_FRAME.

SETTINGS parameters are not negotiated; they describe characteristics of the
sending peer, which can be used by the receiving peer. However, a negotiation
can be implied by the use of SETTINGS - each peer uses SETTINGS to advertise a
set of supported values. The definition of the setting would describe how each
peer combines the two sets to conclude which choice will be used.  SETTINGS does
not provide a mechanism to identify when the choice takes effect.

Different values for the same parameter can be advertised by each peer. For
example, a client might be willing to consume a very large response header,
while servers are more cautious about request size.

Parameters MUST NOT occur more than once in the SETTINGS frame.  A receiver MAY
treat the presence of the same parameter more than once as a connection error of
type HTTP_MALFORMED_FRAME.

The payload of a SETTINGS frame consists of zero or more parameters.  Each
parameter consists of a setting identifier and a value, both encoded as QUIC
variable-length integers.

~~~~~~~~~~~~~~~  drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Identifier (i)                       ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           Value (i)                         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~~~~~~
{: #fig-ext-settings title="SETTINGS parameter format"}

An implementation MUST ignore the contents for any SETTINGS identifier it does
not understand.


#### Defined SETTINGS Parameters {#settings-parameters}

The following settings are defined in HTTP/3:

  SETTINGS_MAX_HEADER_LIST_SIZE (0x6):
  : The default value is unlimited.  See {{header-formatting}} for usage.

  SETTINGS_NUM_PLACEHOLDERS (0x8):
  : The default value is 0.  However, this value SHOULD be set to a non-zero
    value by servers.  See {{placeholders}} for usage.

Setting identifiers of the format `0x1f * N + 0x21` for integer values of N are
reserved to exercise the requirement that unknown identifiers be ignored.  Such
settings have no defined meaning. Endpoints SHOULD include at least one such
setting in their SETTINGS frame. Endpoints MUST NOT consider such settings to
have any meaning upon receipt.

Because the setting has no defined meaning, the value of the setting can be any
value the implementation selects.

Additional settings can be defined by extensions to HTTP/3; see {{extensions}}
for more details.

#### Initialization

An HTTP implementation MUST NOT send frames or requests which would be invalid
based on its current understanding of the peer's settings.  All settings begin
at an initial value, and are updated upon receipt of a SETTINGS frame.  For
servers, the initial value of each client setting is the default value.

For clients using a 1-RTT QUIC connection, the initial value of each server
setting is the default value. When a 0-RTT QUIC connection is being used, the
initial value of each server setting is the value used in the previous session.
Clients MUST store the settings the server provided in the session being resumed
and MUST comply with stored settings until the current server settings are
received.

A server can remember the settings that it advertised, or store an
integrity-protected copy of the values in the ticket and recover the information
when accepting 0-RTT data. A server uses the HTTP/3 settings values in
determining whether to accept 0-RTT data.

A server MAY accept 0-RTT and subsequently provide different settings in its
SETTINGS frame. If 0-RTT data is accepted by the server, its SETTINGS frame MUST
NOT reduce any limits or alter any values that might be violated by the client
with its 0-RTT data.


### PUSH_PROMISE {#frame-push-promise}

The PUSH_PROMISE frame (type=0x05) is used to carry a promised request header
set from server to client on a request stream, as in HTTP/2.

~~~~~~~~~~  drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Push ID (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Header Block (*)                      ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-push-promise title="PUSH_PROMISE frame payload"}

The payload consists of:

Push ID:
: A variable-length integer that identifies the server push operation.  A Push
  ID is used in push stream headers ({{server-push}}), CANCEL_PUSH frames
  ({{frame-cancel-push}}), DUPLICATE_PUSH frames ({{frame-duplicate-push}}), and
  PRIORITY frames ({{frame-priority}}).

Header Block:
: QPACK-compressed request header fields for the promised response.  See [QPACK]
  for more details.

A server MUST NOT use a Push ID that is larger than the client has provided in a
MAX_PUSH_ID frame ({{frame-max-push-id}}) and MUST NOT use the same Push ID in
multiple PUSH_PROMISE frames.  A client MUST treat receipt of a PUSH_PROMISE
that contains a larger Push ID than the client has advertised or a Push ID which
has already been promised as a connection error of type HTTP_MALFORMED_FRAME.

If a PUSH_PROMISE frame is received on either control stream, the recipient MUST
respond with a connection error ({{errors}}) of type HTTP_WRONG_STREAM.

See {{server-push}} for a description of the overall server push mechanism.

### GOAWAY {#frame-goaway}

The GOAWAY frame (type=0x7) is used to initiate graceful shutdown of a
connection by a server.  GOAWAY allows a server to stop accepting new requests
while still finishing processing of previously received requests.  This enables
administrative actions, like server maintenance.  GOAWAY by itself does not
close a connection.

~~~~~~~~~~  drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Stream ID (i)                      ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-goaway title="GOAWAY frame payload"}

The GOAWAY frame is always sent on the control stream. It carries a QUIC Stream
ID for a client-initiated bidirectional stream encoded as a variable-length
integer.  A client MUST treat receipt of a GOAWAY frame containing a Stream ID
of any other type as a connection error of type HTTP_WRONG_STREAM.

Clients do not need to send GOAWAY to initiate a graceful shutdown; they simply
stop making new requests.  A server MUST treat receipt of a GOAWAY frame on any
stream as a connection error ({{errors}}) of type HTTP_UNEXPECTED_FRAME.

The GOAWAY frame applies to the connection, not a specific stream.  A client
MUST treat a GOAWAY frame on a stream other than the control stream as a
connection error ({{errors}}) of type HTTP_UNEXPECTED_FRAME.

See {{connection-shutdown}} for more information on the use of the GOAWAY frame.

### MAX_PUSH_ID {#frame-max-push-id}

The MAX_PUSH_ID frame (type=0xD) is used by clients to control the number of
server pushes that the server can initiate.  This sets the maximum value for a
Push ID that the server can use in a PUSH_PROMISE frame.  Consequently, this
also limits the number of push streams that the server can initiate in addition
to the limit set by the QUIC MAX_STREAM_ID frame.

The MAX_PUSH_ID frame is always sent on the control stream.  Receipt of a
MAX_PUSH_ID frame on any other stream MUST be treated as a connection error of
type HTTP_WRONG_STREAM.

A server MUST NOT send a MAX_PUSH_ID frame.  A client MUST treat the receipt of
a MAX_PUSH_ID frame as a connection error of type HTTP_UNEXPECTED_FRAME.

The maximum Push ID is unset when a connection is created, meaning that a server
cannot push until it receives a MAX_PUSH_ID frame.  A client that wishes to
manage the number of promised server pushes can increase the maximum Push ID by
sending MAX_PUSH_ID frames as the server fulfills or cancels server pushes.

~~~~~~~~~~  drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Push ID (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-max-push title="MAX_PUSH_ID frame payload"}

The MAX_PUSH_ID frame carries a single variable-length integer that identifies
the maximum value for a Push ID that the server can use (see
{{frame-push-promise}}).  A MAX_PUSH_ID frame cannot reduce the maximum Push ID;
receipt of a MAX_PUSH_ID that contains a smaller value than previously received
MUST be treated as a connection error of type HTTP_MALFORMED_FRAME.

### DUPLICATE_PUSH {#frame-duplicate-push}

The DUPLICATE_PUSH frame (type=0xE) is used by servers to indicate that an
existing pushed resource is related to multiple client requests.

The DUPLICATE_PUSH frame is always sent on a request stream.  Receipt of a
DUPLICATE_PUSH frame on any other stream MUST be treated as a connection error
of type HTTP_WRONG_STREAM.

A client MUST NOT send a DUPLICATE_PUSH frame.  A server MUST treat the receipt
of a DUPLICATE_PUSH frame as a connection error of type HTTP_MALFORMED_FRAME.

~~~~~~~~~~  drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Push ID (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-duplicate-push title="DUPLICATE_PUSH frame payload"}

The DUPLICATE_PUSH frame carries a single variable-length integer that
identifies the Push ID of a resource that the server has previously promised
(see {{frame-push-promise}}).

This frame allows the server to use the same server push in response to multiple
concurrent requests.  Referencing the same server push ensures that a promise
can be made in relation to every response in which server push might be needed
without duplicating request headers or pushed responses.

Allowing duplicate references to the same Push ID is primarily to reduce
duplication caused by concurrent requests.  A server SHOULD avoid reusing a Push
ID over a long period.  Clients are likely to consume server push responses and
not retain them for reuse over time.  Clients that see a DUPLICATE_PUSH that
uses a Push ID that they have since consumed and discarded are forced to ignore
the DUPLICATE_PUSH.


### Reserved Frame Types {#frame-grease}

Frame types of the format `0x1f * N + 0x21` for integer values of N are reserved
to exercise the requirement that unknown types be ignored ({{extensions}}).
These frames have no semantics, and can be sent when application-layer padding
is desired. They MAY also be sent on connections where no data is currently
being transferred. Endpoints MUST NOT consider these frames to have any meaning
upon receipt.

The payload and length of the frames are selected in any manner the
implementation chooses.


# HTTP Request Lifecycle

## HTTP Message Exchanges {#request-response}

A client sends an HTTP request on a client-initiated bidirectional QUIC
stream. A client MUST send only a single request on a given stream.
A server sends one or more HTTP responses on the same stream as the request,
as detailed below.

An HTTP message (request or response) consists of:

1. the message header (see {{!RFC7230}}, Section 3.2), sent as a single HEADERS
   frame (see {{frame-headers}}),

2. the payload body (see {{!RFC7230}}, Section 3.3), sent as a series of DATA
   frames (see {{frame-data}}),

3. optionally, one HEADERS frame containing the trailer-part, if present (see
   {{!RFC7230}}, Section 4.1.2).

A server MAY interleave one or more PUSH_PROMISE frames (see
{{frame-push-promise}}) with the frames of a response message. These
PUSH_PROMISE frames are not part of the response; see {{server-push}} for more
details.

The "chunked" transfer encoding defined in Section 4.1 of {{!RFC7230}} MUST NOT
be used.

Trailing header fields are carried in an additional HEADERS frame following the
body. Senders MUST send only one HEADERS frame in the trailers section;
receivers MUST discard any subsequent HEADERS frames.

A response MAY consist of multiple messages when and only when one or more
informational responses (1xx, see {{!RFC7231}}, Section 6.2) precede a final
response to the same request.  Non-final responses do not contain a payload body
or trailers.

An HTTP request/response exchange fully consumes a bidirectional QUIC stream.
After sending a request, a client MUST close the stream for sending.  Unless
using the CONNECT method (see {{the-connect-method}}), clients MUST NOT make
stream closure dependent on receiving a response to their request. After sending
a final response, the server MUST close the stream for sending. At this point,
the QUIC stream is fully closed.

When a stream is closed, this indicates the end of an HTTP message. Because some
messages are large or unbounded, endpoints SHOULD begin processing partial HTTP
messages once enough of the message has been received to make progress.  If a
client stream terminates without enough of the HTTP message to provide a
complete response, the server SHOULD abort its response with the error code
HTTP_INCOMPLETE_REQUEST.

A server can send a complete response prior to the client sending an entire
request if the response does not depend on any portion of the request that has
not been sent and received. When this is true, a server MAY request that the
client abort transmission of a request without error by triggering a QUIC
STOP_SENDING frame with error code HTTP_EARLY_RESPONSE, sending a complete
response, and cleanly closing its stream. Clients MUST NOT discard complete
responses as a result of having their request terminated abruptly, though
clients can always discard responses at their discretion for other reasons.


### Header Formatting and Compression {#header-formatting}

HTTP message headers carry information as a series of key-value pairs, called
header fields. For a listing of registered HTTP header fields, see the "Message
Header Field" registry maintained at
<https://www.iana.org/assignments/message-headers>.

Just as in previous versions of HTTP, header field names are strings of ASCII
characters that are compared in a case-insensitive fashion.  Properties of HTTP
header field names and values are discussed in more detail in Section 3.2 of
{{!RFC7230}}, though the wire rendering in HTTP/3 differs.  As in HTTP/2, header
field names MUST be converted to lowercase prior to their encoding.  A request
or response containing uppercase header field names MUST be treated as
malformed.

As in HTTP/2, HTTP/3 uses special pseudo-header fields beginning with the ':'
character (ASCII 0x3a) to convey the target URI, the method of the request, and
the status code for the response.  These pseudo-header fields are defined in
Section 8.1.2.3 and 8.1.2.4 of {{!RFC7540}}. Pseudo-header fields are not HTTP
header fields.  Endpoints MUST NOT generate pseudo-header fields other than
those defined in {{!RFC7540}}.  The restrictions on the use of pseudo-header
fields in Section 8.1.2.1 of {{!RFC7540}} also apply to HTTP/3.

HTTP/3 uses QPACK header compression as described in [QPACK], a variation of
HPACK which allows the flexibility to avoid header-compression-induced
head-of-line blocking.  See that document for additional details.

An HTTP/3 implementation MAY impose a limit on the maximum size of the header it
will accept on an individual HTTP message; encountering a larger message header
SHOULD be treated as a stream error of type `HTTP_EXCESSIVE_LOAD`.  If an
implementation wishes to advise its peer of this limit, it can be conveyed as a
number of bytes in the `SETTINGS_MAX_HEADER_LIST_SIZE` parameter. The size of a
header list is calculated based on the uncompressed size of header fields,
including the length of the name and value in bytes plus an overhead of 32 bytes
for each header field.

### Request Cancellation and Rejection {#request-cancellation}

Clients can cancel requests by aborting the stream (QUIC RESET_STREAM and/or
STOP_SENDING frames, as appropriate) with an error code of
HTTP_REQUEST_CANCELLED ({{http-error-codes}}).  When the client cancels a
response, it indicates that this response is no longer of interest.
Implementations SHOULD cancel requests by aborting both directions of a stream.

When the server rejects a request without performing any application processing,
it SHOULD abort its response stream with the error code HTTP_REQUEST_REJECTED.
In this context, "processed" means that some data from the stream was passed to
some higher layer of software that might have taken some action as a result. The
client can treat requests rejected by the server as though they had never been
sent at all, thereby allowing them to be retried later on a new connection.
Servers MUST NOT use the HTTP_REQUEST_REJECTED error code for requests which
were partially or fully processed.  When a server abandons a response after
partial processing, it SHOULD abort its response stream with the error code
HTTP_REQUEST_CANCELLED.

When a client sends a STOP_SENDING with HTTP_REQUEST_CANCELLED, a server MAY
send the error code HTTP_REQUEST_REJECTED in the corresponding RESET_STREAM
if no processing was performed.  Clients MUST NOT reset streams with the
HTTP_REQUEST_REJECTED error code except in response to a QUIC STOP_SENDING
frame that contains the same code.

If a stream is cancelled after receiving a complete response, the client MAY
ignore the cancellation and use the response.  However, if a stream is cancelled
after receiving a partial response, the response SHOULD NOT be used.
Automatically retrying such requests is not possible, unless this is otherwise
permitted (e.g., idempotent actions like GET, PUT, or DELETE).


## The CONNECT Method

The pseudo-method CONNECT ({{!RFC7231}}, Section 4.3.6) is primarily used with
HTTP proxies to establish a TLS session with an origin server for the purposes
of interacting with "https" resources. In HTTP/1.x, CONNECT is used to convert
an entire HTTP connection into a tunnel to a remote host. In HTTP/2, the CONNECT
method is used to establish a tunnel over a single HTTP/2 stream to a remote
host for similar purposes.

A CONNECT request in HTTP/3 functions in the same manner as in HTTP/2. The
request MUST be formatted as described in {{!RFC7540}}, Section 8.3. A CONNECT
request that does not conform to these restrictions is malformed. The request
stream MUST NOT be closed at the end of the request.

A proxy that supports CONNECT establishes a TCP connection ({{!RFC0793}}) to the
server identified in the ":authority" pseudo-header field. Once this connection
is successfully established, the proxy sends a HEADERS frame containing a 2xx
series status code to the client, as defined in {{!RFC7231}}, Section 4.3.6.

All DATA frames on the stream correspond to data sent or received on the TCP
connection. Any DATA frame sent by the client is transmitted by the proxy to the
TCP server; data received from the TCP server is packaged into DATA frames by
the proxy. Note that the size and number of TCP segments is not guaranteed to
map predictably to the size and number of HTTP DATA or QUIC STREAM frames.

The TCP connection can be closed by either peer. When the client ends the
request stream (that is, the receive stream at the proxy enters the "Data Recvd"
state), the proxy will set the FIN bit on its connection to the TCP server. When
the proxy receives a packet with the FIN bit set, it will terminate the send
stream that it sends to the client. TCP connections which remain half-closed in
a single direction are not invalid, but are often handled poorly by servers, so
clients SHOULD NOT close a stream for sending while they still expect to receive
data from the target of the CONNECT.

A TCP connection error is signaled with QUIC RESET_STREAM frame. A proxy treats
any error in the TCP connection, which includes receiving a TCP segment with the
RST bit set, as a stream error of type HTTP_CONNECT_ERROR
({{http-error-codes}}).  Correspondingly, a proxy MUST send a TCP segment with
the RST bit set if it detects an error with the stream or the QUIC connection.

## Prioritization {#priority}

HTTP/3 uses a priority scheme similar to that described in {{!RFC7540}}, Section
5.3. In this priority scheme, a given element can be designated as dependent
upon another element. This information is expressed in the PRIORITY frame
{{frame-priority}} which identifies the element and the dependency. The elements
that can be prioritized are:

- Requests, identified by the ID of the request stream
- Pushes, identified by the Push ID of the promised resource
  ({{frame-push-promise}})
- Placeholders, identified by a Placeholder ID

Taken together, the dependencies across all prioritized elements in a connection
form a dependency tree. An element can depend on another element or on the root
of the tree. A reference to an element which is no longer in the tree is treated
as a reference to the root of the tree. The structure of the dependency tree
changes as PRIORITY frames modify the dependency links between prioritized
elements.

Due to reordering between streams, an element can also be prioritized which is
not yet in the tree. Such elements are added to the tree with the requested
priority.

When a prioritized element is first created, it has a default initial weight
of 16 and a default dependency. Requests and placeholders are dependent on the
root of the priority tree; pushes are dependent on the client request on which
the PUSH_PROMISE frame was sent.

Requests may override the default initial values by including a PRIORTIY frame
(see {{frame-priority}}) at the beginning of the stream. These priorities
can be updated by sending a PRIORITY frame on the control stream.

### Placeholders

In HTTP/2, certain implementations used closed or unused streams as placeholders
in describing the relative priority of requests.  This created
confusion as servers could not reliably identify which elements of the priority
tree could be discarded safely. Clients could potentially reference closed
streams long after the server had discarded state, leading to disparate views of
the prioritization the client had attempted to express.

In HTTP/3, a number of placeholders are explicitly permitted by the server using
the `SETTINGS_NUM_PLACEHOLDERS` setting. Because the server commits to
maintaining these placeholders in the prioritization tree, clients can use them
with confidence that the server will not have discarded the state. Clients MUST
NOT send the `SETTINGS_NUM_PLACEHOLDERS` setting; receipt of this setting by a
server MUST be treated as a connection error of type
`HTTP_WRONG_SETTING_DIRECTION`.

Placeholders are identified by an ID between zero and one less than the number
of placeholders the server has permitted.

Like streams, placeholders have priority information associated with them.

### Priority Tree Maintenance

Because placeholders will be used to "root" any persistent structure of the tree
which the client cares about retaining, servers can aggressively prune inactive
regions from the priority tree. For prioritization purposes, a node in the tree
is considered "inactive" when the corresponding stream has been closed for at
least two round-trip times (using any reasonable estimate available on the
server).  This delay helps mitigate race conditions where the server has pruned
a node the client believed was still active and used as a Stream Dependency.

Specifically, the server MAY at any time:

- Identify and discard branches of the tree containing only inactive nodes
  (i.e. a node with only other inactive nodes as descendants, along with those
  descendants)
- Identify and condense interior regions of the tree containing only inactive
  nodes, allocating weight appropriately

~~~~~~~~~~  drawing
    x                x                 x
    |                |                 |
    P                P                 P
   / \               |                 |
  I   I     ==>      I      ==>        A
     / \             |                 |
    A   I            A                 A
    |                |
    A                A
~~~~~~~~~~
{: #fig-pruning title="Example of Priority Tree Pruning"}

In the example in {{fig-pruning}}, `P` represents a Placeholder, `A` represents
an active node, and `I` represents an inactive node.  In the first step, the
server discards two inactive branches (each a single node).  In the second step,
the server condenses an interior inactive node.  Note that these transformations
will result in no change in the resources allocated to a particular active
stream.

Clients SHOULD assume the server is actively performing such pruning and SHOULD
NOT declare a dependency on a stream it knows to have been closed.

## Server Push

HTTP/3 server push is similar to what is described in HTTP/2 {{!RFC7540}}, but
uses different mechanisms.

Each server push is identified by a unique Push ID. This Push ID is used in a
single PUSH_PROMISE frame (see {{frame-push-promise}}) which carries the request
headers, possibly included in one or more DUPLICATE_PUSH frames (see
{{frame-duplicate-push}}), then included with the push stream which ultimately
fulfills those promises.

Server push is only enabled on a connection when a client sends a MAX_PUSH_ID
frame (see {{frame-max-push-id}}). A server cannot use server push until it
receives a MAX_PUSH_ID frame. A client sends additional MAX_PUSH_ID frames to
control the number of pushes that a server can promise. A server SHOULD use Push
IDs sequentially, starting at 0. A client MUST treat receipt of a push stream
with a Push ID that is greater than the maximum Push ID as a connection error of
type HTTP_LIMIT_EXCEEDED.

The header of the request message is carried by a PUSH_PROMISE frame (see
{{frame-push-promise}}) on the request stream which generated the push. This
allows the server push to be associated with a client request. Ordering of a
PUSH_PROMISE in relation to certain parts of the response is important (see
Section 8.2.1 of {{!RFC7540}}).  Promised requests MUST conform to the
requirements in Section 8.2 of {{!RFC7540}}.

The same server push can be associated with additional client requests using a
DUPLICATE_PUSH frame (see {{frame-duplicate-push}}).  Ordering of a
DUPLICATE_PUSH in relation to certain parts of the response is similarly
important.  Due to reordering, DUPLICATE_PUSH frames can arrive before the
corresponding PUSH_PROMISE frame, in which case the request headers of the push
would not be immediately available.  Clients which receive a DUPLICATE_PUSH
frame for an as-yet-unknown Push ID can either delay generating new requests for
content referenced following the DUPLICATE_PUSH frame until the request headers
become available, or can initiate requests for discovered resources and cancel
the requests if the requested resource is already being pushed.

When a server later fulfills a promise, the server push response is conveyed on
a push stream (see {{push-streams}}). The push stream identifies the Push ID of
the promise that it fulfills, then contains a response to the promised request
using the same format described for responses in {{request-response}}.

If a promised server push is not needed by the client, the client SHOULD send a
CANCEL_PUSH frame. If the push stream is already open or opens after sending the
CANCEL_PUSH frame, a QUIC STOP_SENDING frame with an appropriate error code can
also be used (e.g., HTTP_PUSH_REFUSED, HTTP_PUSH_ALREADY_IN_CACHE; see
{{errors}}). This asks the server not to transfer additional data and indicates
that it will be discarded upon receipt.

# Connection Closure

Once established, an HTTP/3 connection can be used for many requests and
responses over time until the connection is closed.  Connection closure can
happen in any of several different ways.

## Idle Connections

Each QUIC endpoint declares an idle timeout during the handshake.  If the
connection remains idle (no packets received) for longer than this duration, the
peer will assume that the connection has been closed.  HTTP/3 implementations
will need to open a new connection for new requests if the existing connection
has been idle for longer than the server's advertised idle timeout, and SHOULD
do so if approaching the idle timeout.

HTTP clients are expected to request that the transport keep connections open
while there are responses outstanding for requests or server pushes, as
described in Section 19.2 of {{QUIC-TRANSPORT}}. If the client is not expecting
a response from the server, allowing an idle connection to time out is preferred
over expending effort maintaining a connection that might not be needed.  A
gateway MAY maintain connections in anticipation of need rather than incur the
latency cost of connection establishment to servers. Servers SHOULD NOT actively
keep connections open.

## 连接关闭（Connection Shutdown）

即使连接不是空闲的，任何一个端都可以决定停止使用连接，并让连接正常关闭。由于客户端
驱动请求生成，因此客户端通过不在连接上发送其他请求来执行连接关闭；与先前请求相关联的
响应和推送响应将继续完成。服务器通过与客户端通信来执行相同的功能。

服务器通过发送GOAWAY帧({{frame-goaway}})启动连接关闭。GOAWAY帧指示在较低流ID上的
客户端发起的请求在此连接中被处理或可能被处理，而在指示的流ID和更大流ID上的请求被拒绝。
这使客户端和服务器能够在连接关闭之前就哪些请求被接受达成一致。此标识符**可能**低于
QUIC MAX_STREAM_ID 帧标识的流限制，如果没有请求已被处理，则该标识符**可能**为零。
发送GOAWAY帧后，服务器**不应**增加QUIC MAX_STREAM_ID限制。

GOAWAY发送后，服务器**必须**拒绝使用标识符大于或等于最后一个流ID的流发送的请求。
客户端在收到GOAWAY后**禁止**在连接上发送新的请求，尽管请求可能已经在传输中。可以
为新请求建立新连接。

如果客户端在流ID大于或等于GOAWAY帧中指示的流ID的流上发送请求，则这些请求被视为
被拒绝({{request-cancellation}})。客户端**应该**取消对此ID以上的流的任何请求。
如果未处理这些请求，服务器还**可能**拒绝ID低于指示ID的流上的请求。

流ID小于GOAWAY帧中流ID的请求可能已被处理；只有在成功完成、单独重置或连接终止之前，
才能知道它们的状态。

当预先知道连接关闭时，服务器应该发送GOAWAY帧，即使提前通知很小，这样远程对端
就可以知道请求是否已被部分处理。例如，如果HTTP客户端在服务器关闭QUIC连接的同时
发送POST请求，则如果服务器未发送GOAWAY帧以指示它可能对哪些流执行了操作，那么
客户端无法知道服务器是否开始处理该POST请求。

当服务器关闭连接时，无法重试请求的客户端将丢失正在运行的所有请求。服务器**可能**会
发送多个GOAWAY帧，表示不同的流ID，但**禁止**增加它们在最后一个流ID中发送的值，
因为客户端可能已经在另一个连接上重试了未处理的请求。尝试正常关闭连接的服务器**应该**
发送初始GOAWAY帧，且最后一个流ID设置为QUIC的MAX_STREAM_ID的当前值，此后**不应**
增加MAX_STREAM_ID。这向客户端发出信号，表明即将关闭，并且禁止进一步的请求。
在为任何传输中请求留出时间(至少一个往返时间)后，服务器**可能**会发送另一个更新后
且是最后的流ID的GOAWAY帧。这可以确保连接可以在不丢失请求的情况下干净地关闭。

一旦所有已接受的请求都得到处理，服务器就可以允许连接变得空闲，或者**可以**启动连接
的立即关闭。完成正常关闭的端点**应该**在关闭连接时使用HTTP_NO_ERROR代码。

## 立即关闭应用程序

一个HTTP/3的实现可以随时立即关闭QUIC连接，这会发送QUIC CONNECTION_CLOSE帧到对端；
此帧中的错误代码告诉对端为什么要关闭连接。有关关闭连接时可以使用的错误代码，
请参见{{errors}}。

在关闭连接之前，可能会发送GOAWAY帧以允许客户端重试某些请求。将GOAWAY帧包含在QUIC
CONNECTION_CLOSE帧所在的数据包中可以提高客户端接收该帧的机会。

## 传输关闭

由于各种原因，QUIC传输可能会向应用层表明连接已终止。这可能是由于对端显式关闭、传输层
错误或网络拓扑更改中断连接所致。

如果连接在没有GOAWAY帧的情况下终止，客户端**必须**假设发送的任何请求(无论是全部还是部分)
都可能已被处理。

# HTTP/3的扩展(Extensions to HTTP/3) {#extensions}

HTTP/3允许对协议进行扩展。在本节描述的限制范围内，协议扩展可用于提供附加服务或更改
协议的任何方面。扩展仅在单个HTTP/3连接的范围内有效。

这适用于本文档中定义的协议元素。这不影响现有的HTTP扩展选项，例如定义新方法、状态码
或标头字段。

扩展允许使用新的帧类型({{frames}})、新的设置({{settings-parameters}})、新的
错误码({{errors}})或新的单向流类型({{unidirectional-streams}})。建立了用于
管理这些扩展点的注册表：帧类型({{iana-frames}})、设置({{iana-settings}})、
错误码({{iana-error-codes}})和流类型({{iana-stream-types}})。

实现**必须**忽略所有可扩展协议元素中的未知或不受支持的值。实现**必须**丢弃具有
未知或不支持类型的帧和单向流。这意味着在没有事先安排或协商的情况下，扩展可以安全
地使用这些扩展点中的任何一个。

在使用之前，必须协商可以更改现有协议组件语义的扩展。例如，在对端发出可接受的正面
信号之前，不能使用更改HEADERS帧布局的扩展。在这种情况下，也可能有必要在修改后的布局
生效时进行协调。

本文档并不要求使用特定的方法来协商扩展的使用，但提到可以使用设置({{settings-parameters}})
来实现此目的。如果两个对端都设置了表示愿意使用扩展的值，则可以使用扩展。如果将设置用于扩展协商
则**必须**以这样的方式定义默认值：如果省略该设置，则禁用扩展。


# 错误处理（Error Handling） {#errors}

QUIC允许应用程序在遇到错误时突然终止(重置)单个流或整个连接。这些错误称为“流错误”或
“连接错误”，在{{QUIC-TRANSPORT}}中有详细说明。端点**可以**选择将流错误视为连接错误。

本节介绍特定于HTTP/3的错误代码，这些代码可用于表示连接或流错误的原因。

## HTTP/3 Error Codes {#http-error-codes}

The following error codes are defined for use in QUIC RESET_STREAM frames,
STOP_SENDING frames, and CONNECTION_CLOSE frames when using HTTP/3.

HTTP_NO_ERROR (0x00):
: No error.  This is used when the connection or stream needs to be closed, but
  there is no error to signal.

HTTP_WRONG_SETTING_DIRECTION (0x01):
: A client-only setting was sent by a server, or a server-only setting by a
  client.

HTTP_PUSH_REFUSED (0x02):
: The server has attempted to push content which the client will not accept
  on this connection.

HTTP_INTERNAL_ERROR (0x03):
: An internal error has occurred in the HTTP stack.

HTTP_PUSH_ALREADY_IN_CACHE (0x04):
: The server has attempted to push content which the client has cached.

HTTP_REQUEST_CANCELLED (0x05):
: The request or its response is cancelled.

HTTP_INCOMPLETE_REQUEST (0x06):
: The client's stream terminated without containing a fully-formed request.

HTTP_CONNECT_ERROR (0x07):
: The connection established in response to a CONNECT request was reset or
  abnormally closed.

HTTP_EXCESSIVE_LOAD (0x08):
: The endpoint detected that its peer is exhibiting a behavior that might be
  generating excessive load.

HTTP_VERSION_FALLBACK (0x09):
: The requested operation cannot be served over HTTP/3.  The
  peer should retry over HTTP/1.1.

HTTP_WRONG_STREAM (0x0A):
: A frame was received on a stream where it is not permitted.

HTTP_LIMIT_EXCEEDED (0x0B):
: A Stream ID, Push ID, or Placeholder ID greater than the current maximum for
  that identifier was referenced.

HTTP_DUPLICATE_PUSH (0x0C):
: A Push ID was referenced in two different stream headers.

HTTP_UNKNOWN_STREAM_TYPE (0x0D):
: A unidirectional stream header contained an unknown stream type.

HTTP_WRONG_STREAM_COUNT (0x0E):
: A unidirectional stream type was used more times than is permitted by that
  type.

HTTP_CLOSED_CRITICAL_STREAM (0x0F):
: A stream required by the connection was closed or reset.

HTTP_WRONG_STREAM_DIRECTION (0x0010):
: A unidirectional stream type was used by a peer which is not permitted to do
  so.

HTTP_EARLY_RESPONSE (0x0011):
: The remainder of the client's request is not needed to produce a response.
  For use in STOP_SENDING only.

HTTP_MISSING_SETTINGS (0x0012):
: No SETTINGS frame was received at the beginning of the control stream.

HTTP_UNEXPECTED_FRAME (0x0013):
: A frame was received which was not permitted in the current state.

HTTP_REQUEST_REJECTED (0x0014):
: A server rejected a request without performing any application processing.

HTTP_GENERAL_PROTOCOL_ERROR (0x00FF):
: Peer violated protocol requirements in a way which doesn't match a more
  specific error code, or endpoint declines to use the more specific error code.

HTTP_MALFORMED_FRAME (0x01XX):
: An error in a specific frame type.  If the frame type is `0xfe` or less, the
  type is included as the last byte of the error code.  For example, an error in
  a MAX_PUSH_ID frame would be indicated with the code (0x10D).  The last byte
  `0xff` is used to indicate any frame type greater than `0xfe`.


# Security Considerations

The security considerations of HTTP/3 should be comparable to those of HTTP/2
with TLS.  Note that where HTTP/2 employs PADDING frames and Padding fields in
other frames to make a connection more resistant to traffic analysis, HTTP/3 can
rely on QUIC PADDING frames or employ the reserved frame and stream types
discussed in {{frame-grease}} and {{stream-grease}}.

When HTTP Alternative Services is used for discovery for HTTP/3 endpoints, the
security considerations of {{!ALTSVC}} also apply.

Several protocol elements contain nested length elements, typically in the form
of frames with an explicit length containing variable-length integers.  This
could pose a security risk to an incautious implementer.  An implementation MUST
ensure that the length of a frame exactly matches the length of the fields it
contains.

Certain HTTP implementations use the client address for logging or
access-control purposes.  Since a QUIC client's address might change during a
connection (and future versions might support simultaneous use of multiple
addresses), such implementations will need to either actively retrieve the
client's current address or addresses when they are relevant or explicitly
accept that the original address might change.


# IANA Considerations

## Registration of HTTP/3 Identification String

This document creates a new registration for the identification of
HTTP/3 in the "Application Layer Protocol Negotiation (ALPN)
Protocol IDs" registry established in {{?RFC7301}}.

The "h3" string identifies HTTP/3:

  Protocol:
  : HTTP/3

  Identification Sequence:
  : 0x68 0x33 ("h3")

  Specification:
  : This document

## Registration of QUIC Version Hint Alt-Svc Parameter

This document creates a new registration for version-negotiation hints in the
"Hypertext Transfer Protocol (HTTP) Alt-Svc Parameter" registry established in
{{!RFC7838}}.

  Parameter:
  : "quic"

  Specification:
  : This document, {{alt-svc-version-hint}}

## Frame Types {#iana-frames}

This document establishes a registry for HTTP/3 frame type codes. The "HTTP/3
Frame Type" registry governs a 62-bit space. This space is split into three
spaces that are governed by different policies. Values between `0x00` and `0x3f`
(in hexadecimal) are assigned via the Standards Action or IESG Review policies
{{!RFC8126}}. Values from `0x40` to `0x3fff` operate on the Specification
Required policy {{!RFC8126}}. All other values are assigned to Private Use
{{!RFC8126}}.

While this registry is separate from the "HTTP/2 Frame Type" registry defined in
{{RFC7540}}, it is preferable that the assignments parallel each other where the
code spaces overlap.  If an entry is present in only one registry, every effort
SHOULD be made to avoid assigning the corresponding value to an unrelated
operation.

New entries in this registry require the following information:

Frame Type:
: A name or label for the frame type.

Code:
: The 62-bit code assigned to the frame type.

Specification:
: A reference to a specification that includes a description of the frame layout
  and its semantics, including any parts of the frame that are conditionally
  present.

The entries in the following table are registered by this document.

| ---------------- | ------ | -------------------------- |
| Frame Type       |  Code  | Specification              |
| ---------------- | :----: | -------------------------- |
| DATA             |  0x0   | {{frame-data}}             |
| HEADERS          |  0x1   | {{frame-headers}}          |
| PRIORITY         |  0x2   | {{frame-priority}}         |
| CANCEL_PUSH      |  0x3   | {{frame-cancel-push}}      |
| SETTINGS         |  0x4   | {{frame-settings}}         |
| PUSH_PROMISE     |  0x5   | {{frame-push-promise}}     |
| Reserved         |  0x6   | N/A                        |
| GOAWAY           |  0x7   | {{frame-goaway}}           |
| Reserved         |  0x8   | N/A                        |
| Reserved         |  0x9   | N/A                        |
| MAX_PUSH_ID      |  0xD   | {{frame-max-push-id}}      |
| DUPLICATE_PUSH   |  0xE   | {{frame-duplicate-push}}   |
| ---------------- | ------ | -------------------------- |

Additionally, each code of the format `0x1f * N + 0x21` for integer values of N
(that is, `0x21`, `0x40`, ..., through `0x‭3FFFFFFFFFFFFFFE‬`) MUST NOT be
assigned by IANA.

## Settings Parameters {#iana-settings}

This document establishes a registry for HTTP/3 settings.  The "HTTP/3 Settings"
registry governs a 62-bit space. This space is split into three spaces that are
governed by different policies. Values between `0x00` and `0x3f` (in
hexadecimal) are assigned via the Standards Action or IESG Review policies
{{!RFC8126}}. Values from `0x40` to `0x3fff` operate on the Specification
Required policy {{!RFC8126}}. All other values are assigned to Private Use
{{!RFC8126}}.  The designated experts are the same as those for the "HTTP/2
Settings" registry defined in {{RFC7540}}.

While this registry is separate from the "HTTP/2 Settings" registry defined in
{{RFC7540}}, it is preferable that the assignments parallel each other.  If an
entry is present in only one registry, every effort SHOULD be made to avoid
assigning the corresponding value to an unrelated operation.

New registrations are advised to provide the following information:

Name:
: A symbolic name for the setting.  Specifying a setting name is optional.

Code:
: The 62-bit code assigned to the setting.

Specification:
: An optional reference to a specification that describes the use of the
  setting.

The entries in the following table are registered by this document.

| ---------------------------- | ------ | ------------------------- |
| Setting Name                 |  Code  | Specification             |
| ---------------------------- | :----: | ------------------------- |
| Reserved                     |  0x2   | N/A                       |
| Reserved                     |  0x3   | N/A                       |
| Reserved                     |  0x4   | N/A                       |
| Reserved                     |  0x5   | N/A                       |
| MAX_HEADER_LIST_SIZE         |  0x6   | {{settings-parameters}}   |
| NUM_PLACEHOLDERS             |  0x8   | {{settings-parameters}}   |
| ---------------------------- | ------ | ------------------------- |

Additionally, each code of the format `0x1f * N + 0x21` for integer values of N
(that is, `0x21`, `0x40`, ..., through `0x‭3FFFFFFFFFFFFFFE‬`) MUST NOT be
assigned by IANA.

## Error Codes {#iana-error-codes}

This document establishes a registry for HTTP/3 error codes. The "HTTP/3 Error
Code" registry manages a 16-bit space.  The "HTTP/3 Error Code" registry
operates under the "Expert Review" policy {{?RFC8126}}.

Registrations for error codes are required to include a description
of the error code.  An expert reviewer is advised to examine new
registrations for possible duplication with existing error codes.
Use of existing registrations is to be encouraged, but not mandated.

New registrations are advised to provide the following information:

Name:
: A name for the error code.  Specifying an error code name is optional.

Code:
: The 16-bit error code value.

Description:
: A brief description of the error code semantics, longer if no detailed
  specification is provided.

Specification:
: An optional reference for a specification that defines the error code.

The entries in the following table are registered by this document.

| ----------------------------------- | ---------- | ---------------------------------------- | ---------------------- |
| Name                                | Code       | Description                              | Specification          |
| ----------------------------------- | ---------- | ---------------------------------------- | ---------------------- |
| HTTP_NO_ERROR                       | 0x0000     | No error                                 | {{http-error-codes}}   |
| HTTP_WRONG_SETTING_DIRECTION        | 0x0001     | Setting sent in wrong direction          | {{http-error-codes}}   |
| HTTP_PUSH_REFUSED                   | 0x0002     | Client refused pushed content            | {{http-error-codes}}   |
| HTTP_INTERNAL_ERROR                 | 0x0003     | Internal error                           | {{http-error-codes}}   |
| HTTP_PUSH_ALREADY_IN_CACHE          | 0x0004     | Pushed content already cached            | {{http-error-codes}}   |
| HTTP_REQUEST_CANCELLED              | 0x0005     | Data no longer needed                    | {{http-error-codes}}   |
| HTTP_INCOMPLETE_REQUEST             | 0x0006     | Stream terminated early                  | {{http-error-codes}}   |
| HTTP_CONNECT_ERROR                  | 0x0007     | TCP reset or error on CONNECT request    | {{http-error-codes}}   |
| HTTP_EXCESSIVE_LOAD                 | 0x0008     | Peer generating excessive load           | {{http-error-codes}}   |
| HTTP_VERSION_FALLBACK               | 0x0009     | Retry over HTTP/1.1                      | {{http-error-codes}}   |
| HTTP_WRONG_STREAM                   | 0x000A     | A frame was sent on the wrong stream     | {{http-error-codes}}   |
| HTTP_LIMIT_EXCEEDED                 | 0x000B     | An identifier limit was exceeded         | {{http-error-codes}}   |
| HTTP_DUPLICATE_PUSH                 | 0x000C     | Push ID was fulfilled multiple times     | {{http-error-codes}}   |
| HTTP_UNKNOWN_STREAM_TYPE            | 0x000D     | Unknown unidirectional stream type       | {{http-error-codes}}   |
| HTTP_WRONG_STREAM_COUNT             | 0x000E     | Too many unidirectional streams          | {{http-error-codes}}   |
| HTTP_CLOSED_CRITICAL_STREAM         | 0x000F     | Critical stream was closed               | {{http-error-codes}}   |
| HTTP_WRONG_STREAM_DIRECTION         | 0x0010     | Unidirectional stream in wrong direction | {{http-error-codes}}   |
| HTTP_EARLY_RESPONSE                 | 0x0011     | Remainder of request not needed          | {{http-error-codes}}   |
| HTTP_MISSING_SETTINGS               | 0x0012     | No SETTINGS frame received               | {{http-error-codes}}   |
| HTTP_UNEXPECTED_FRAME               | 0x0013     | Frame not permitted in the current state | {{http-error-codes}}   |
| HTTP_REQUEST_REJECTED               | 0x0014     | Request not processed                    | {{http-error-codes}}   |
| HTTP_MALFORMED_FRAME                | 0x01XX     | Error in frame formatting                | {{http-error-codes}}   |
| ----------------------------------- | ---------- | ---------------------------------------- | ---------------------- |

## Stream Types {#iana-stream-types}

This document establishes a registry for HTTP/3 unidirectional stream types. The
"HTTP/3 Stream Type" registry governs a 62-bit space. This space is split into
three spaces that are governed by different policies. Values between `0x00` and
0x3f (in hexadecimal) are assigned via the Standards Action or IESG Review
policies {{!RFC8126}}. Values from `0x40` to `0x3fff` operate on the
Specification Required policy {{!RFC8126}}. All other values are assigned to
Private Use {{!RFC8126}}.

New entries in this registry require the following information:

Stream Type:
: A name or label for the stream type.

Code:
: The 62-bit code assigned to the stream type.

Specification:
: A reference to a specification that includes a description of the stream type,
  including the layout semantics of its payload.

Sender:
: Which endpoint on a connection may initiate a stream of this type. Values are
  "Client", "Server", or "Both".

The entries in the following table are registered by this document.

| ---------------- | ------ | -------------------------- | ------ |
| Stream Type      |  Code  | Specification              | Sender |
| ---------------- | :----: | -------------------------- | ------ |
| Control Stream   |  0x00  | {{control-streams}}        | Both   |
| Push Stream      |  0x01  | {{server-push}}            | Server |
| ---------------- | ------ | -------------------------- | ------ |

Additionally, each code of the format `0x1f * N + 0x21` for integer values of N
(that is, `0x21`, `0x40`, ..., through `0x‭3FFFFFFFFFFFFFFE‬`) MUST NOT be
assigned by IANA.

--- back

# Considerations for Transitioning from HTTP/2

HTTP/3 is strongly informed by HTTP/2, and bears many similarities.  This
section describes the approach taken to design HTTP/3, points out important
differences from HTTP/2, and describes how to map HTTP/2 extensions into HTTP/3.

HTTP/3 begins from the premise that similarity to HTTP/2 is preferable, but not
a hard requirement.  HTTP/3 departs from HTTP/2 primarily where necessary to
accommodate the differences in behavior between QUIC and TCP (lack of ordering,
support for streams).  We intend to avoid gratuitous changes which make it
difficult or impossible to build extensions with the same semantics applicable
to both protocols at once.

These departures are noted in this section.

## Streams {#h2-streams}

HTTP/3 permits use of a larger number of streams (2^62-1) than HTTP/2.  The
considerations about exhaustion of stream identifier space apply, though the
space is significantly larger such that it is likely that other limits in QUIC
are reached first, such as the limit on the connection flow control window.

## HTTP Frame Types {#h2-frames}

Many framing concepts from HTTP/2 can be elided on QUIC, because the transport
deals with them. Because frames are already on a stream, they can omit the
stream number. Because frames do not block multiplexing (QUIC's multiplexing
occurs below this layer), the support for variable-maximum-length packets can be
removed. Because stream termination is handled by QUIC, an END_STREAM flag is
not required.  This permits the removal of the Flags field from the generic
frame layout.

Frame payloads are largely drawn from {{!RFC7540}}. However, QUIC includes many
features (e.g., flow control) which are also present in HTTP/2. In these cases,
the HTTP mapping does not re-implement them. As a result, several HTTP/2 frame
types are not required in HTTP/3. Where an HTTP/2-defined frame is no longer
used, the frame ID has been reserved in order to maximize portability between
HTTP/2 and HTTP/3 implementations. However, even equivalent frames between the
two mappings are not identical.

Many of the differences arise from the fact that HTTP/2 provides an absolute
ordering between frames across all streams, while QUIC provides this guarantee
on each stream only.  As a result, if a frame type makes assumptions that frames
from different streams will still be received in the order sent, HTTP/3 will
break them.

For example, implicit in the HTTP/2 prioritization scheme is the notion of
in-order delivery of priority changes (i.e., dependency tree mutations): since
operations on the dependency tree such as reparenting a subtree are not
commutative, both sender and receiver must apply them in the same order to
ensure that both sides have a consistent view of the stream dependency tree.
HTTP/2 specifies priority assignments in PRIORITY frames and (optionally) in
HEADERS frames. To achieve in-order delivery of priority changes in HTTP/3,
PRIORITY frames are sent on the control stream and exclusive prioritization
has been removed.

Likewise, HPACK was designed with the assumption of in-order delivery. A
sequence of encoded header blocks must arrive (and be decoded) at an endpoint in
the same order in which they were encoded. This ensures that the dynamic state
at the two endpoints remains in sync.  As a result, HTTP/3 uses a modified
version of HPACK, described in [QPACK].

Frame type definitions in HTTP/3 often use the QUIC variable-length integer
encoding.  In particular, Stream IDs use this encoding, which allow for a larger
range of possible values than the encoding used in HTTP/2.  Some frames in
HTTP/3 use an identifier rather than a Stream ID (e.g. Push IDs in PRIORITY
frames). Redefinition of the encoding of extension frame types might be
necessary if the encoding includes a Stream ID.

Because the Flags field is not present in generic HTTP/3 frames, those frames
which depend on the presence of flags need to allocate space for flags as part
of their frame payload.

Other than this issue, frame type HTTP/2 extensions are typically portable to
QUIC simply by replacing Stream 0 in HTTP/2 with a control stream in HTTP/3.
HTTP/3 extensions will not assume ordering, but would not be harmed by ordering,
and would be portable to HTTP/2 in the same manner.

Below is a listing of how each HTTP/2 frame type is mapped:

DATA (0x0):
: Padding is not defined in HTTP/3 frames.  See {{frame-data}}.

HEADERS (0x1):
: As described above, the PRIORITY region of HEADERS is not supported. A
  separate PRIORITY frame MUST be used. Padding is not defined in HTTP/3 frames.
  See {{frame-headers}}.

PRIORITY (0x2):
: As described above, the PRIORITY frame is sent on the control stream and can
  reference a variety of identifiers.  See {{frame-priority}}.

RST_STREAM (0x3):
: RST_STREAM frames do not exist, since QUIC provides stream lifecycle
  management.  The same code point is used for the CANCEL_PUSH frame
  ({{frame-cancel-push}}).

SETTINGS (0x4):
: SETTINGS frames are sent only at the beginning of the connection.  See
  {{frame-settings}} and {{h2-settings}}.

PUSH_PROMISE (0x5):
: The PUSH_PROMISE does not reference a stream; instead the push stream
  references the PUSH_PROMISE frame using a Push ID.  See
  {{frame-push-promise}}.

PING (0x6):
: PING frames do not exist, since QUIC provides equivalent functionality.

GOAWAY (0x7):
: GOAWAY is sent only from server to client and does not contain an error code.
  See {{frame-goaway}}.

WINDOW_UPDATE (0x8):
: WINDOW_UPDATE frames do not exist, since QUIC provides flow control.

CONTINUATION (0x9):
: CONTINUATION frames do not exist; instead, larger HEADERS/PUSH_PROMISE
  frames than HTTP/2 are permitted.

Frame types defined by extensions to HTTP/2 need to be separately registered for
HTTP/3 if still applicable.  The IDs of frames defined in {{!RFC7540}} have been
reserved for simplicity.  Note that the frame type space in HTTP/3 is
substantially larger (62 bits versus 8 bits), so many HTTP/3 frame types have no
equivalent HTTP/2 code points.   See {{iana-frames}}.

## HTTP/2 SETTINGS Parameters {#h2-settings}

An important difference from HTTP/2 is that settings are sent once, at the
beginning of the connection, and thereafter cannot change.  This eliminates
many corner cases around synchronization of changes.

Some transport-level options that HTTP/2 specifies via the SETTINGS frame are
superseded by QUIC transport parameters in HTTP/3. The HTTP-level options that
are retained in HTTP/3 have the same value as in HTTP/2.

Below is a listing of how each HTTP/2 SETTINGS parameter is mapped:

SETTINGS_HEADER_TABLE_SIZE:
: See [QPACK].

SETTINGS_ENABLE_PUSH:
: This is removed in favor of the MAX_PUSH_ID which provides a more granular
  control over server push.

SETTINGS_MAX_CONCURRENT_STREAMS:
: QUIC controls the largest open Stream ID as part of its flow control logic.
  Specifying SETTINGS_MAX_CONCURRENT_STREAMS in the SETTINGS frame is an error.

SETTINGS_INITIAL_WINDOW_SIZE:
: QUIC requires both stream and connection flow control window sizes to be
  specified in the initial transport handshake.  Specifying
  SETTINGS_INITIAL_WINDOW_SIZE in the SETTINGS frame is an error.

SETTINGS_MAX_FRAME_SIZE:
: This setting has no equivalent in HTTP/3.  Specifying it in the SETTINGS frame
  is an error.

SETTINGS_MAX_HEADER_LIST_SIZE:
: See {{settings-parameters}}.

In HTTP/3, setting values are variable-length integers (6, 14, 30, or 62 bits
long) rather than fixed-length 32-bit fields as in HTTP/2.  This will often
produce a shorter encoding, but can produce a longer encoding for settings which
use the full 32-bit space.  Settings ported from HTTP/2 might choose to redefine
the format of their settings to avoid using the 62-bit encoding.

Settings need to be defined separately for HTTP/2 and HTTP/3. The IDs of
settings defined in {{!RFC7540}} have been reserved for simplicity.  Note that
the settings identifier space in HTTP/3 is substantially larger (62 bits versus
16 bits), so many HTTP/3 settings have no equivalent HTTP/2 code point. See
{{iana-settings}}.


## HTTP/2 Error Codes

QUIC has the same concepts of "stream" and "connection" errors that HTTP/2
provides. However, there is no direct portability of HTTP/2 error codes.

The HTTP/2 error codes defined in Section 7 of {{!RFC7540}} map to the HTTP/3
error codes as follows:

NO_ERROR (0x0):
: HTTP_NO_ERROR in {{http-error-codes}}.

PROTOCOL_ERROR (0x1):
: No single mapping.  See new HTTP_MALFORMED_FRAME error codes defined in
  {{http-error-codes}}.

INTERNAL_ERROR (0x2):
: HTTP_INTERNAL_ERROR in {{http-error-codes}}.

FLOW_CONTROL_ERROR (0x3):
: Not applicable, since QUIC handles flow control.  Would provoke a
  QUIC_FLOW_CONTROL_RECEIVED_TOO_MUCH_DATA from the QUIC layer.

SETTINGS_TIMEOUT (0x4):
: Not applicable, since no acknowledgement of SETTINGS is defined.

STREAM_CLOSED (0x5):
: Not applicable, since QUIC handles stream management.  Would provoke a
  QUIC_STREAM_DATA_AFTER_TERMINATION from the QUIC layer.

FRAME_SIZE_ERROR (0x6):
: HTTP_MALFORMED_FRAME error codes defined in {{http-error-codes}}.

REFUSED_STREAM (0x7):
: HTTP_REQUEST_REJECTED (in {{http-error-codes}}) is used to indicate that a
  request was not processed. Otherwise, not applicable because QUIC handles
  stream management.  A STREAM_ID_ERROR at the QUIC layer is used for streams
  that are improperly opened.

CANCEL (0x8):
: HTTP_REQUEST_CANCELLED in {{http-error-codes}}.

COMPRESSION_ERROR (0x9):
: Multiple error codes are defined in [QPACK].

CONNECT_ERROR (0xa):
: HTTP_CONNECT_ERROR in {{http-error-codes}}.

ENHANCE_YOUR_CALM (0xb):
: HTTP_EXCESSIVE_LOAD in {{http-error-codes}}.

INADEQUATE_SECURITY (0xc):
: Not applicable, since QUIC is assumed to provide sufficient security on all
  connections.

HTTP_1_1_REQUIRED (0xd):
: HTTP_VERSION_FALLBACK in {{http-error-codes}}.

Error codes need to be defined for HTTP/2 and HTTP/3 separately.  See
{{iana-error-codes}}.

# Change Log

> **RFC Editor's Note:**  Please remove this section prior to publication of a
> final version of this document.

## Since draft-ietf-quic-http-17

- HTTP_REQUEST_REJECTED is used to indicate a request can be retried (#2106,
  #2325)
- Changed error code for GOAWAY on the wrong stream (#2231, #2343)


## Since draft-ietf-quic-http-16

- Rename "HTTP/QUIC" to "HTTP/3" (#1973)
- Changes to PRIORITY frame (#1865, #2075)
  - Permitted as first frame of request streams
  - Remove exclusive reprioritization
  - Changes to Prioritized Element Type bits
- Define DUPLICATE_PUSH frame to refer to another PUSH_PROMISE (#2072)
- Set defaults for settings, allow request before receiving SETTINGS (#1809,
  #1846, #2038)
- Clarify message processing rules for streams that aren't closed (#1972, #2003)
- Removed reservation of error code 0 and moved HTTP_NO_ERROR to this value
  (#1922)
- Removed prohibition of zero-length DATA frames (#2098)


## Since draft-ietf-quic-http-15

Substantial editorial reorganization; no technical changes.

## Since draft-ietf-quic-http-14

- Recommend sensible values for QUIC transport parameters (#1720,#1806)
- Define error for missing SETTINGS frame (#1697,#1808)
- Setting values are variable-length integers (#1556,#1807) and do not have
  separate maximum values (#1820)
- Expanded discussion of connection closure (#1599,#1717,#1712)
- HTTP_VERSION_FALLBACK falls back to HTTP/1.1 (#1677,#1685)

## Since draft-ietf-quic-http-13

- Reserved some frame types for grease (#1333, #1446)
- Unknown unidirectional stream types are tolerated, not errors; some reserved
  for grease (#1490, #1525)
- Require settings to be remembered for 0-RTT, prohibit reductions (#1541,
  #1641)
- Specify behavior for truncated requests (#1596, #1643)

## Since draft-ietf-quic-http-12

- TLS SNI extension isn't mandatory if an alternative method is used (#1459,
  #1462, #1466)
- Removed flags from HTTP/3 frames (#1388, #1398)
- Reserved frame types and settings for use in preserving extensibility (#1333,
  #1446)
- Added general error code (#1391, #1397)
- Unidirectional streams carry a type byte and are extensible (#910,#1359)
- Priority mechanism now uses explicit placeholders to enable persistent
  structure in the tree (#441,#1421,#1422)

## Since draft-ietf-quic-http-11

- Moved QPACK table updates and acknowledgments to dedicated streams (#1121,
  #1122, #1238)

## Since draft-ietf-quic-http-10

- Settings need to be remembered when attempting and accepting 0-RTT (#1157,
  #1207)

## Since draft-ietf-quic-http-09

- Selected QCRAM for header compression (#228, #1117)
- The server_name TLS extension is now mandatory (#296, #495)
- Specified handling of unsupported versions in Alt-Svc (#1093, #1097)

## Since draft-ietf-quic-http-08

- Clarified connection coalescing rules (#940, #1024)

## Since draft-ietf-quic-http-07

- Changes for integer encodings in QUIC (#595,#905)
- Use unidirectional streams as appropriate (#515, #240, #281, #886)
- Improvement to the description of GOAWAY (#604, #898)
- Improve description of server push usage (#947, #950, #957)

## Since draft-ietf-quic-http-06

- Track changes in QUIC error code usage (#485)

## Since draft-ietf-quic-http-05

- Made push ID sequential, add MAX_PUSH_ID, remove SETTINGS_ENABLE_PUSH (#709)
- Guidance about keep-alive and QUIC PINGs (#729)
- Expanded text on GOAWAY and cancellation (#757)

## Since draft-ietf-quic-http-04

- Cite RFC 5234 (#404)
- Return to a single stream per request (#245,#557)
- Use separate frame type and settings registries from HTTP/2 (#81)
- SETTINGS_ENABLE_PUSH instead of SETTINGS_DISABLE_PUSH (#477)
- Restored GOAWAY (#696)
- Identify server push using Push ID rather than a stream ID (#702,#281)
- DATA frames cannot be empty (#700)

## Since draft-ietf-quic-http-03

None.

## Since draft-ietf-quic-http-02

- Track changes in transport draft

## Since draft-ietf-quic-http-01

- SETTINGS changes (#181):
    - SETTINGS can be sent only once at the start of a connection;
      no changes thereafter
    - SETTINGS_ACK removed
    - Settings can only occur in the SETTINGS frame a single time
    - Boolean format updated

- Alt-Svc parameter changed from "v" to "quic"; format updated (#229)
- Closing the connection control stream or any message control stream is a
  fatal error (#176)
- HPACK Sequence counter can wrap (#173)
- 0-RTT guidance added
- Guide to differences from HTTP/2 and porting HTTP/2 extensions added
  (#127,#242)

## Since draft-ietf-quic-http-00

- Changed "HTTP/2-over-QUIC" to "HTTP/QUIC" throughout (#11,#29)
- Changed from using HTTP/2 framing within Stream 3 to new framing format and
  two-stream-per-request model (#71,#72,#73)
- Adopted SETTINGS format from draft-bishop-httpbis-extended-settings-01
- Reworked SETTINGS_ACK to account for indeterminate inter-stream order (#75)
- Described CONNECT pseudo-method (#95)
- Updated ALPN token and Alt-Svc guidance (#13,#87)
- Application-layer-defined error codes (#19,#74)


## Since draft-shade-quic-http2-mapping-00

- Adopted as base for draft-ietf-quic-http
- Updated authors/editors list

# Acknowledgements
{:numbered="false"}

The original authors of this specification were Robbie Shade and Mike Warres.

A substantial portion of Mike's contribution was supported by Microsoft during
his employment there.
