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


# Introduction

HTTP semantics are used for a broad range of services on the Internet. These
semantics have commonly been used with two different TCP mappings, HTTP/1.1 and
HTTP/2.  HTTP/2 introduced a framing and multiplexing layer to improve latency
without modifying the transport layer.  However, TCP's lack of visibility into
parallel requests in both mappings limited the possible performance gains.

The QUIC transport protocol incorporates stream multiplexing and per-stream flow
control, similar to that provided by the HTTP/2 framing layer. By providing
reliability at the stream level and congestion control across the entire
connection, it has the capability to improve the performance of HTTP compared to
a TCP mapping.  QUIC also incorporates TLS 1.3 at the transport layer, offering
comparable security to running TLS over TCP, but with improved connection setup
latency (unless TCP Fast Open {{?RFC7413}}} is used).

This document defines a mapping of HTTP semantics over the QUIC transport
protocol, drawing heavily on the design of HTTP/2. This document identifies
HTTP/2 features that are subsumed by QUIC, and describes how the other features
can be implemented atop QUIC.

QUIC is described in {{QUIC-TRANSPORT}}.  For a full description of HTTP/2, see
{{!RFC7540}}.


## Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in BCP 14 {{!RFC2119}} {{!RFC8174}}
when, and only when, they appear in all capitals, as shown here.

Field definitions are given in Augmented Backus-Naur Form (ABNF), as defined in
{{!RFC5234}}.

This document uses the variable-length integer encoding from
{{QUIC-TRANSPORT}}.

Protocol elements called "frames" exist in both this document and
{{QUIC-TRANSPORT}}. Where frames from {{QUIC-TRANSPORT}} are referenced, the
frame name will be prefaced with "QUIC."  For example, "QUIC CONNECTION_CLOSE
frames."  References without this preface refer to frames defined in {{frames}}.


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

# 流映射与使用(Stream Mapping and Usage) {#stream-mapping}

QUIC流提供了可靠的按顺序的字节交付，但不能保证其他流上的字节的交付顺序。
在网络上，数据被框入QUIC STREAM帧，但是这个帧对HTTP帧层是不可见的。
传输层缓冲区和接收到QUIC流帧的订单，将其中包含的数据作为可靠的字节流公开给应用程序。
尽管QUIC允许在流HTTP/3中无序交付，但它没有使用这个特性。

QUIC流可以是单向的，只携带数据从发起者到接收者，也可以是双向的。
流可以由客户机或服务器发起。有关QUIC流的更多细节，请参见{{QUIC-TRANSPORT}}。

当HTTP头和数据通过QUIC发送时，QUIC层处理大部分流管理。
使用QUIC时，HTTP不需要进行任何单独的多路
复用——通过QUIC流发送的数据总是映射到特定的HTTP事务或连接上下文。


## 双向流 (Bidirectional Streams)

所有客户端发起的双向流都用于HTTP请求和响应。
双向流确保响应可以很容易地与请求关联。
这意味着客户机的第一个请求发生在QUIC流0上，随后的请求发生在流4、8上，依此类推。
为了允许这些流打开，HTTP/3客户机应该为QUIC传输参数
`initial_max_stream_data_bidi_local`发送非零值。
HTTP/3服务器应该为QUIC传输参数`initial_max_stream_data_bidi_remote`和
`initial_max_bidi_streams`发送非零值。
建议`initial_max_bidi_streams`不小于100，以避免不必要地并行性限制。

这些流携带与请求/响应相关的帧(参见{{request-response}})。
当流干净地终止时，如果流上的最后一帧被截断，则**必须**将此视为连接错误
(请参阅 {{http-error-codes}}中的HTTP_MALFORMED_FRAME)。
突然终止的流可以在帧中的任何位置重置。

HTTP/3不使用服务器发起的双向流;客户端**必须**省略
或为QUIC传输参数`initial_max_bidi_streams`指定一个零值。


## 单向流 (Unidirectional Streams)

单向流，无论在哪个方向，都用于一系列的目的。
目的由流类型表示，该类型在流开始时作为可变长度整数发送。
遵循该整数的数据的格式和结构由流类型决定。


~~~~~~~~~~ drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        流类型(Stream Type) (i)                      ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-stream-header title="单向流头(Unidirectional Stream Header)"}

一些流类型被保留了({{stream-grease}})。
本文档定义了两种流类型:控制流({{control-streams}})和推送流({{push-streams}})。
其他流类型可以通过扩展到HTTP/3来定义;有关详细信息，请参见{{extensions}}。

客户机和服务器都**应该**为QUIC传输参数`initial_max_uni_streams`发送三个或更多的值。

如果流标头指示接收方不支持的流类型，则不能使用流的其余部分，因为语义未知。
未知流类型的接收方**可以**使用HTTP_UNKNOWN_STREAM_TYPE错误代码触发
QUIC STOP_SENDING帧，但**不能**将此类流视为任何类型的错误。

实现**可能**在不知道对等方是否支持流类型之前发送流类型。
但是，在知道对等方支持流类型之前，
**不能**发送可以修改现有协议组件(包括QPACK或其他扩展)的状态或语义的流类型。


除非另有说明，否则发送方可以关闭或重置单向流。
接收器**必须**容忍单向流在接收单向流标头之前被关闭或重置。

###  控制流(Control Streams)

控制流由`0x00`的流类型表示。这个流上的数据由HTTP/3帧组成，如{{frames}}所定义。

每一方**必须**在连接开始时启动一个控制流，并将其SETTINGS帧作为该流上的第一个帧发送。
如果控制流的第一帧是任何其他帧类型，
则**必须**将其视为HTTP_MISSING_SETTINGS类型的连接错误。
每个对端只允许一个控制流;接收声称是控制流的第二个流时，
**必须**将其视为类型为HTTP_WRONG_STREAM_COUNT的连接错误。发送方**不能**关闭控制流。
如果控制流在任何时刻关闭，则**必须**将其视为HTTP_CLOSED_CRITICAL_STREAM类型的连接错误。

使用一对单向流而不是单个双向流。这使得任何一方都可以尽快发送数据。
根据是否在连接上启用0-RTT，客户机或服务器都可以在加密握手完成后首先发送流数据。

### 推送流(Push Streams)

push流由`0x01`类型的流表示，后面跟着它所实现的承诺的Push ID，
该ID被编码为一个可变长度整数。
此流上的其余数据由HTTP/3帧组成，如{{frames}}中定义的那样，并完成一个承诺的服务器推送。
{{server-push}}描述了服务器推送和Push IDs。

只有服务器可以推送;如果服务器接收到客户机发起的推送流，
则**必须**将其视为类型为HTTP_WRONG_STREAM_DIRECTI的流错误


~~~~~~~~~~ drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           0x01 (i)                          ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Push ID (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-push-stream-header title="推送流头(Push Stream Header)"}

每个Push ID**必须**只能在Push流头中使用一次。
如果一个push流报头包含一个在另一个push流报头中使用的push ID，
客户端**必须**将其视为HTTP_DUPLICATE_PUSH类型的连接错误。

### 保留流类型(Reserved Stream Types) {#stream-grease}

保留格式为`0x1f * N + 0x21`的N的整数值的流类型，以执行忽略未知类型的要求。
这些流没有语义，可以在需要应用程序层填充时发送。
它们也**可以**在当前没有传输数据的连接上发送。
终端在接收时**不能**认为这些流有任何意义。

流的有效负载和长度可以由实现选择的任何方式来选择。

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

### PRIORITY {#frame-priority}

The PRIORITY (type=0x02) frame specifies the client-advised priority of a
request, server push or placeholder.

A PRIORITY frame identifies an element to prioritize, and an element upon which
it depends.  A Prioritized ID or Dependency ID identifies a client-initiated
request using the corresponding stream ID, a server push using a Push ID (see
{{frame-push-promise}}), or a placeholder using a Placeholder ID (see
{{placeholders}}).

When a client initiates a request, a PRIORITY frame MAY be sent as the first
frame of the stream, creating a dependency on an existing element.  In order to
ensure that prioritization is processed in a consistent order, any subsequent
PRIORITY frames for that request MUST be sent on the control stream.  A
PRIORITY frame received after other frames on a request stream MUST be treated
as a stream error of type HTTP_UNEXPECTED_FRAME.

If, by the time a new request stream is opened, its priority information
has already been received via the control stream, the PRIORITY frame
sent on the request stream MUST be ignored.

~~~~~~~~~~  drawing
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|PT |DT | Empty |         [Prioritized Element ID (i)]        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                [Element Dependency ID (i)]                  ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Weight (8)  |
+-+-+-+-+-+-+-+-+
~~~~~~~~~~
{: #fig-priority title="PRIORITY frame payload"}

The PRIORITY frame payload has the following fields:

  PT (Prioritized Element Type):
  : A two-bit field indicating the type of element being prioritized (see
    {{prioritized-element-types}}). When sent on a request stream, this MUST be
    set to `11`.  When sent on the control stream, this MUST NOT be set to `11`.

  DT (Element Dependency Type):
  : A two-bit field indicating the type of element being depended on (see
    {{element-dependency-types}}).

  Empty:
  : A four-bit field which MUST be zero when sent and MUST be ignored
    on receipt.

  Prioritized Element ID:
  : A variable-length integer that identifies the element being prioritized.
    Depending on the value of Prioritized Type, this contains the Stream ID of a
    request stream, the Push ID of a promised resource, a Placeholder ID of a
    placeholder, or is absent.

  Element Dependency ID:
  : A variable-length integer that identifies the element on which a dependency
    is being expressed. Depending on the value of Dependency Type, this contains
    the Stream ID of a request stream, the Push ID of a promised resource, the
    Placeholder ID of a placeholder, or is absent.  For details of
    dependencies, see {{priority}} and {{!RFC7540}}, Section 5.3.

  Weight:
  : An unsigned 8-bit integer representing a priority weight for the prioritized
    element (see {{!RFC7540}}, Section 5.3). Add one to the value to obtain a
    weight between 1 and 256.

The values for the Prioritized Element Type ({{prioritized-element-types}}) and
Element Dependency Type ({{element-dependency-types}}) imply the interpretation
of the associated Element ID fields.

| PT Bits | Type Description | Prioritized Element ID Contents |
| ------- | ---------------- | ------------------------------- |
| 00      | Request stream   | Stream ID                       |
| 01      | Push stream      | Push ID                         |
| 10      | Placeholder      | Placeholder ID                  |
| 11      | Current stream   | Absent                          |
{: #prioritized-element-types title="Prioritized Element Types"}

| DT Bits | Type Description | Element Dependency ID Contents |
| ------- | ---------------- | ------------------------------ |
| 00      | Request stream   | Stream ID                      |
| 01      | Push stream      | Push ID                        |
| 10      | Placeholder      | Placeholder ID                 |
| 11      | Root of the tree | Absent                         |
{: #element-dependency-types title="Element Dependency Types"}

Note that unlike in {{!RFC7540}}, the root of the tree cannot be referenced
using a Stream ID of 0, as in QUIC stream 0 carries a valid HTTP request.  The
root of the tree cannot be reprioritized.  A PRIORITY frame sent on a request
stream with the Prioritized Element Type set to any value other than `11` or
which expresses a dependency on a request with a greater Stream ID than the
current stream MUST be treated as a stream error of type HTTP_MALFORMED_FRAME.
Likewise, a PRIORITY frame sent on a control stream with the Prioritized Element
Type set to `11` MUST be treated as a connection error of type
HTTP_MALFORMED_FRAME.

When a PRIORITY frame claims to reference a request, the associated ID MUST
identify a client-initiated bidirectional stream.  A server MUST treat receipt
of a PRIORITY frame identifying a stream of any other type as a connection error
of type HTTP_MALFORMED_FRAME.

A PRIORITY frame that references a non-existent Push ID, a Placeholder ID
greater than the server's limit, or a Stream ID the client is not yet permitted
to open MUST be treated as an HTTP_LIMIT_EXCEEDED error.

A PRIORITY frame received on any stream other than a request or control stream
MUST be treated as a connection error of type HTTP_WRONG_STREAM.

PRIORITY frames received by a client MUST be treated as a stream error of type
HTTP_UNEXPECTED_FRAME.

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

### 优先级树的维护(Priority Tree Maintenance)

因为占位符将用于作为客户机所关心的用于保持任何树的持久性结构的根，
服务器可以从优先级树中积极地删除不活动的区域。
出于优先级的目的，当相应的流被关闭至少两次(使用服务器上可用的任何合理估计)时，
树中的节点被认为是“非活动的”。
这种延迟有助于缓解竞争条件，即服务器修剪了客户端认为的仍处于活动状态的节点，
并将其用作流依赖项。

具体而言，服务器**可以**在任何时候:

- 识别并丢弃只包含非活动节点的树的分支(即只包含其他非活动节点的节点及其后代)

- 识别并压缩只包含不活动节点的树的内部区域，并适当地分配权重

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
{: #fig-pruning title="优先级树修剪的例子"}

在{{fig-pruning}}中的示例中，`P` 表示占位符，`A` 表示活动节点，`I`表示非活动节点。
在第一步中，服务器丢弃两个不活动的分支(每个分支都是一个节点)。
在第二步中，服务器将压缩一个内部非活动节点。
注意，这些转换不会导致分配给特定活动流的资源发生变化。

客户端**应该**假设服务器正在积极地执行这样的修剪，并且**不应该**声明对它知道已关闭的流的依赖关系。

Clients SHOULD assume the server is actively performing such pruning and SHOULD
NOT declare a dependency on a stream it knows to have been closed.

## 服务器推送 (Server Push)

HTTP/3服务器推送与HTTP/2{{!RFC7540}}中描述的类似，但是使用不同的机制。

每个服务器推送由一个唯一的Push ID确认。
这个Push ID用于单个含有请求头的PUSH_PROMISE帧(参见{{frame-push-promise}}),
它可能包含在一个或多个DUPLICATE_PUSH帧(见{{frame-duplicate-push}}),
然后包含在最终实现这些承诺的推送流中。

只有当客户机发送MAX_PUSH_ID帧(参见{{frame-max-push-id}})时，
服务器推送才会在连接上启用。
服务器在接收MAX_PUSH_ID帧之前不能使用服务器推送。
客户机发送额外的MAX_PUSH_ID帧来控制服务器可以承诺的推送数量。
服务器**应该**顺序使用Push id，从0开始。
客户机**必须**将带有大于最大推送ID的推送流的接收视为HTTP_LIMIT_EXCEEDED类型的连接错误。

请求消息的头由PUSH_PROMISE帧(参见{{frame-push-promise}})在生成推送的请求流上携带。
这允许服务器推送与客户机请求相关联。PUSH_PROMISE相对于响应的某些部分的排序很重要
(参见{{!RFC7540}}的8.2.1节)。
承诺的请求**必须**符合{{!RFC7540}}第8.2节中的要求。

同一个服务器推送可以使用一个DUPLICATE_PUSH帧与其他客户机的请求
关联(参见{{frame-duplicate-push}})。
与响应的某些部分相关的DUPLICATE_PUSH的排序也同样重要。
由于重新排序，DUPLICATE_PUSH帧可以在相应的PUSH_PROMISE帧之前到达，
在这种情况下，push的请求头不会立即可用。
客户端收取到DUPLICATE_PUSH帧到Push ID可以延迟产生新的要求内容引用DUPLICATE_PUSH帧后,
直到请求头可用,或者可以启动发现资源的请求和取消请求如果所请求的资源已经被推送。

当服务器稍后实现一个承诺时，服务器的推送响应将在一个推送流中传递(参见{{push-streams}})。
推送流标识它所实现的承诺的Push ID，然后包含对承诺请求的响应，
使用与{{request-response}}中描述的响应相同的格式。

如果客户端不需要承诺的服务器推送，客户端**应该**发送CANCEL_PUSH帧。
如果推送流已经打开或者在发送CANCEL_PUSH帧之后打开，
也可以使用一个带有适当错误代码的QUIC STOP_SENDING帧
(例如HTTP_PUSH_REFUSED, HTTP_PUSH_ALREADY_IN_CACHE;详情见{{errors}});
这要求服务器不要传输额外的数据，并表明它将在接收时被丢弃。

# 连接关闭 (Connection Closure)

一旦建立了HTTP/3连接，就可以随着时间的推移对许多请求和响应使用HTTP/3连接，
直到连接关闭为止。连接关闭可以以几种不同的方式做到。

## 空闲连接 (Idle Connections)

每个QUIC终端在握手期间声明一个空闲超时。
如果连接保持空闲(没有接收到数据包)的时间超过此时间，对端将假定连接已关闭。
HTTP/3的实现将需要为新请求打开一个新连接，
如果现有连接的空闲时间超过了服务器所声明的空闲超时时间，
并且在接近空闲超时时**应该**这样做。

如{{QUIC-TRANSPORT}}的第19.2节所述，
当请求或服务器推送有未完成的响应时，HTTP客户端需要请求传输保持连接打开。
如果客户机不期望服务器响应，那么允许空闲连接超时比花费精力维护可能不需要的连接更可取。
网关**可以**在预期需要时保持连接，而不是承担到服务器建立连接的延迟成本。
服务器**不应**主动保持连接打开。.

## Connection Shutdown

Even when a connection is not idle, either endpoint can decide to stop using the
connection and let the connection close gracefully.  Since clients drive request
generation, clients perform a connection shutdown by not sending additional
requests on the connection; responses and pushed responses associated to
previous requests will continue to completion.  Servers perform the same
function by communicating with clients.

Servers initiate the shutdown of a connection by sending a GOAWAY frame
({{frame-goaway}}).  The GOAWAY frame indicates that client-initiated requests
on lower stream IDs were or might be processed in this connection, while
requests on the indicated stream ID and greater were rejected. This enables
client and server to agree on which requests were accepted prior to the
connection shutdown.  This identifier MAY be lower than the stream limit
identified by a QUIC MAX_STREAM_ID frame, and MAY be zero if no requests were
processed.  Servers SHOULD NOT increase the QUIC MAX_STREAM_ID limit after
sending a GOAWAY frame.

Once GOAWAY is sent, the server MUST reject requests sent on streams with an
identifier greater than or equal to the indicated last Stream ID.  Clients MUST
NOT send new requests on the connection after receiving GOAWAY, although
requests might already be in transit. A new connection can be established for
new requests.

If the client has sent requests on streams with a Stream ID greater than or
equal to that indicated in the GOAWAY frame, those requests are considered
rejected ({{request-cancellation}}).  Clients SHOULD cancel any requests on
streams above this ID.  Servers MAY also reject requests on streams below the
indicated ID if these requests were not processed.

Requests on Stream IDs less than the Stream ID in the GOAWAY frame might have
been processed; their status cannot be known until they are completed
successfully, reset individually, or the connection terminates.

Servers SHOULD send a GOAWAY frame when the closing of a connection is known
in advance, even if the advance notice is small, so that the remote peer can
know whether a request has been partially processed or not.  For example, if an
HTTP client sends a POST at the same time that a server closes a QUIC
connection, the client cannot know if the server started to process that POST
request if the server does not send a GOAWAY frame to indicate what streams it
might have acted on.

A client that is unable to retry requests loses all requests that are in flight
when the server closes the connection.  A server MAY send multiple GOAWAY frames
indicating different stream IDs, but MUST NOT increase the value they send in
the last Stream ID, since clients might already have retried unprocessed
requests on another connection.  A server that is attempting to gracefully shut
down a connection SHOULD send an initial GOAWAY frame with the last Stream ID
set to the current value of QUIC's MAX_STREAM_ID and SHOULD NOT increase the
MAX_STREAM_ID thereafter.  This signals to the client that a shutdown is
imminent and that initiating further requests is prohibited.  After allowing
time for any in-flight requests (at least one round-trip time), the server MAY
send another GOAWAY frame with an updated last Stream ID.  This ensures that a
connection can be cleanly shut down without losing requests.

Once all accepted requests have been processed, the server can permit the
connection to become idle, or MAY initiate an immediate closure of the
connection.  An endpoint that completes a graceful shutdown SHOULD use the
HTTP_NO_ERROR code when closing the connection.

## Immediate Application Closure

An HTTP/3 implementation can immediately close the QUIC connection at any time.
This results in sending a QUIC CONNECTION_CLOSE frame to the peer; the error
code in this frame indicates to the peer why the connection is being closed.
See {{errors}} for error codes which can be used when closing a connection.

Before closing the connection, a GOAWAY MAY be sent to allow the client to retry
some requests.  Including the GOAWAY frame in the same packet as the QUIC
CONNECTION_CLOSE frame improves the chances of the frame being received by
clients.

## Transport Closure

For various reasons, the QUIC transport could indicate to the application layer
that the connection has terminated.  This might be due to an explicit closure
by the peer, a transport-level error, or a change in network topology which
interrupts connectivity.

If a connection terminates without a GOAWAY frame, clients MUST assume that any
request which was sent, whether in whole or in part, might have been processed.

# Extensions to HTTP/3 {#extensions}

HTTP/3 permits extension of the protocol.  Within the limitations described in
this section, protocol extensions can be used to provide additional services or
alter any aspect of the protocol.  Extensions are effective only within the
scope of a single HTTP/3 connection.

This applies to the protocol elements defined in this document.  This does not
affect the existing options for extending HTTP, such as defining new methods,
status codes, or header fields.

Extensions are permitted to use new frame types ({{frames}}), new settings
({{settings-parameters}}), new error codes ({{errors}}), or new unidirectional
stream types ({{unidirectional-streams}}).  Registries are established for
managing these extension points: frame types ({{iana-frames}}), settings
({{iana-settings}}), error codes ({{iana-error-codes}}), and stream types
({{iana-stream-types}}).

Implementations MUST ignore unknown or unsupported values in all extensible
protocol elements.  Implementations MUST discard frames and unidirectional
streams that have unknown or unsupported types.  This means that any of these
extension points can be safely used by extensions without prior arrangement or
negotiation.

Extensions that could change the semantics of existing protocol components MUST
be negotiated before being used.  For example, an extension that changes the
layout of the HEADERS frame cannot be used until the peer has given a positive
signal that this is acceptable. In this case, it could also be necessary to
coordinate when the revised layout comes into effect.

This document doesn't mandate a specific method for negotiating the use of an
extension but notes that a setting ({{settings-parameters}}) could be used for
that purpose.  If both peers set a value that indicates willingness to use the
extension, then the extension can be used.  If a setting is used for extension
negotiation, the default value MUST be defined in such a fashion that the
extension is disabled if the setting is omitted.


# Error Handling {#errors}

QUIC allows the application to abruptly terminate (reset) individual streams or
the entire connection when an error is encountered.  These are referred to as
"stream errors" or "connection errors" and are described in more detail in
{{QUIC-TRANSPORT}}.  An endpoint MAY choose to treat a stream error as a
connection error.

This section describes HTTP/3-specific error codes which can be used to express
the cause of a connection or stream error.

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
