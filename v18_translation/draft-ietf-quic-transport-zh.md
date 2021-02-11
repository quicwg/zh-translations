---
title: "QUIC: A UDP-Based Multiplexed and Secure Transport"
abbrev: QUIC Transport Protocol
docname: draft-ietf-quic-transport-latest
date: {DATE}
category: std
ipr: trust200902
area: Transport
workgroup: QUIC

stand_alone: yes
pi: [toc, sortrefs, symrefs, docmapping]

author:
  -
    ins: J. Iyengar
    name: Jana Iyengar
    org: Fastly
    email: jri.ietf@gmail.com
    role: editor
  -
    ins: M. Thomson
    name: Martin Thomson
    org: Mozilla
    email: mt@lowentropy.net
    role: editor

normative:

  QUIC-RECOVERY:
    title: "QUIC Loss Detection and Congestion Control"
    date: {DATE}
    seriesinfo:
      Internet-Draft: draft-ietf-quic-recovery-latest
    author:
      -
        ins: J. Iyengar
        name: Jana Iyengar
        org: Fastly
        role: editor
      -
        ins: I. Swett
        name: Ian Swett
        org: Google
        role: editor

  QUIC-TLS:
    title: "Using Transport Layer Security (TLS) to Secure QUIC"
    date: {DATE}
    seriesinfo:
      Internet-Draft: draft-ietf-quic-tls-latest
    author:
      -
        ins: M. Thomson
        name: Martin Thomson
        org: Mozilla
        role: editor
      -
        ins: S. Turner
        name: Sean Turner
        org: sn3rd
        role: editor

informative:

  QUIC-INVARIANTS:
    title: "Version-Independent Properties of QUIC"
    date: {DATE}
    seriesinfo:
      Internet-Draft: draft-ietf-quic-invariants-latest
    author:
      -
        ins: M. Thomson
        name: Martin Thomson
        org: Mozilla

  EARLY-DESIGN:
    title: "QUIC: Multiplexed Transport Over UDP"
    author:
      - ins: J. Roskind
    date: 2013-12-02
    target: "https://goo.gl/dMVtFi"

  SLOWLORIS:
    title: "Welcome to Slowloris..."
    author:
      - ins: R. RSnake Hansen
    date: 2009-06
    target:
     "https://web.archive.org/web/20150315054838/http://ha.ckers.org/slowloris/"


--- abstract

This document defines the core of the QUIC transport protocol.  Accompanying
documents describe QUIC's loss detection and congestion control and the use of
TLS for key negotiation.


--- note_Note_to_Readers

Discussion of this draft takes place on the QUIC working group mailing list
(quic@ietf.org), which is archived at
\<https://mailarchive.ietf.org/arch/search/?email_list=quic\>.

Working Group information can be found at \<https://github.com/quicwg\>; source
code and issues list for this draft can be found at
\<https://github.com/quicwg/base-drafts/labels/-transport\>.

--- middle

# 简介

QUIC 是一个安全通用的多路复用的传输协议，它提供了：

* 流多路复用

* 流和连接级别的流量控制

* 低延迟的连接建立

* 连接迁移和 NAT 重新绑定的恢复能力

* 认证加密的报头和数据

QUIC 使用了 UDP 作为底层协议来避免需要对旧的终端操作系统
或中间层进行修改。为了避免对中间层的依赖,
QUIC 验证所有的报头和加密大部分他交换的数据，
包括 QUIC 自身的信号。


## 文档结构(Introduction)

这个文档描述了 QUIC 协议的核心部分，如下结构所构建

* 流是 QUIC 提供的基础服务抽象
  - {{streams}} 描述了关于流的核心概念
  - {{stream-states}} 提供了一个流状态的参考模型
  - {{flow-control}} 概述了流量控制的运作方式

* 连接是 QUIC 协议终端数据通信的上下文环境
  - {{connections}} 描述了关于连接的核心概念
  - {{version-negotiation}} 描述了版本协商
  - {{handshake}} 详细描述了建立连接的过程
  - {{address-validation}} 指定了关键的拒绝服务的缓解机制
  - {{migration}} 描述了终端如何将连接迁移到新的网络路径
  - {{termination}} 列举了关闭一个连接的选项
  - {{error-handling}} 提供了异常处理的通用指引

* 包和帧是 QUIC 通信的基本单元
  - {{packets-frames}} 描述了关于包与帧概念
  - {{packetization}} 定义了传输、重传和确认数据的模型
  - {{packet-size}} 制定了管理包大小的规则

* 最后， QUIC 协议各元素编码细节：
  - {{versions}} （版本）
  - {{integer-encoding}} （数字编码）
  - {{packet-formats}} （包头）
  - {{transport-parameter-encoding}} （传输参数）
  - {{frame-formats}} （帧）
  - {{error-codes}} （异常）

附带文档描述了 QUIC 的丢包检测和拥塞控制{{QUIC-RECOVERY}}
，以及 TLS 在密钥协商中的使用{{QUIC-TLS}}。

此文档定义了 QUIC 版本 1，
它符合定义在{{QUIC-INVARIANTS}}中的协议非变量。


## 术语和定义(Document Structure)

关键词 **"必须(MUST)”， "禁止(MUST NOT)"， "必需(REQUIRED)"，
"应当(SHALL)"， "应当不(SHALL NOT)"， "应该(SHOULD)"，
"不应该(SHOULD NOT)"， "推荐(RECOMMENDED)"，
"不推荐(NOT RECOMMENDED)"， "可以(MAY)"， "可选(OPTIONAL)"**
在这篇文档中将会如 BCP 14 {{!RFC2119}} {{!RFC8174}} 中描述的，
当且仅当他们如此例子显示的以加粗的形式出现时。
文档中常用的术语在下方描述。

|术语 | 解释 |
|:---- |:----|
|QUIC | 此文档所描述的传输协议。QUIC是一个名字，不是一个首字母缩写。|
|QUIC 包 | 在一个 UDP 报文中可封装的 QUIC 最小单元。多个 QUIC 包可以被封装在单个 UDP 报文中。|
|终端 | 可以通过生成，接收，处理 QUIC 包参与 QUIC 连接生成的实体。在 QUIC 中仅有两种类型的终端，客户端与服务端。|
|客户端 | 创建 QUIC 连接的终端。|
|服务端 | 接收到来的 QUIC 连接的终端。|
|连接 ID | 一种不透明的标识符，用于标识终端上的 QUIC 连接。每个终端都为其对端设置一个值，以便将其包含在发送到该终端的数据包中。|
|流 | QUIC 连接中有序字节的单向或双向通道。一个 QUIC 连接可以同时传输多个流。|
|应用 | 可以使用 QUIC 发送与接收数据的实体。|


## 注解公约(Terms and Definitions)

本文档中的包和帧的示意图使用在{{?RFC2360}}
章节3.1中的格式进行描述，并加上了如下额外的公约。

\[x\]:
: 表示 x 是可选的

x (A):
: 表示 x 长度为 A 比特

x (A/B/C) ...:
: 表示 x 长度为 A 或 B 或 C 比特中的一种

x (i) ...:
: 表示 x 使用了在{{integer-encoding}}中描述的可变长度编码

x (*) ...:
: 表示 x 是可变长度的

# 流(Streams)

QUIC中的流向应用提供一个有序的轻量级字节流的抽象。
QUIC流可以近似的看成一条长度可变的信息。

流可以通过发送数据创建。流管理相关的其他流程均以
最小开销来设计，包含结束、取消和流量控制。
举例来说，在单一STREAM帧（{{frame-stream}} 内可以完
成以下操作：开启一个流，在流中传送数据，然后关闭它。
但流也可以是长寿，甚至在连接期间一直持续。

任意终端均可创建、关闭流，
以及使用它发送数据（可与其他流交错发送数据）。
且任意终端均可发起一个流。
但QUIC不提供任何方法确保不同流上的字节之间的有序。

QUIC允许同时操作任意数量的流，
并且可在任何流上发送任意数量的数据。
但受流量控制约束{{flow-control}}和流限制。

## 流的种类和识别(Stream Types and Identifiers) {#stream-id}

流可选单向或双向。
单向流在一个方向上传输数据：从流的发起者到它的对端。
双向流则允许双方互相发送数据。

在一个连接中的流通过一个被称为流ID的数值来识别。
该值为可变长整数({{integer-encoding}})，
一个QUIC终端 **禁止** 在一个连接中重用流ID。

流ID的第二个最低有效位（0x2）区分
双向流（该位设置为0）和单向流（该位设置为1）。

由此，通过流ID的2个最低有效位可以把流分为4种，
如表1所示。{{stream-id-types}}

| Bits | Stream Type                      |
|:-----|:---------------------------------|
| 0x0  | Client-Initiated, Bidirectional  |
| 0x1  | Server-Initiated, Bidirectional  |
| 0x2  | Client-Initiated, Unidirectional |
| 0x3  | Server-Initiated, Unidirectional |
{: #stream-id-types title="Stream ID Types"}

在每种类型中，流创建时都伴随有序递增的流ID。
不按顺序使用的流ID将导致该类型的所有具有较
低编号的流ID的流也被开启。

第一个客户端打开的双向的流id为0


## 收发数据(Sending and Receiving Data)

STREAM帧（第19.8节）封装了应用程序发送的数据。
终端使用STREAM帧中的Stream ID和Offset字段
按顺序放置数据。
终端**必须**能将流数据转换有序字节流传递给应用程序。
这要求终端能接收并缓冲所有
无序数据直到受声明的流量控制限制。

QUIC本身没有对无序传输的流数据做出具体限制。
但是在实际的协议实现中，
**可以**选择传递无序数据给应用程序。

终端可以从流中多次接收有相同流
offset的数据，此时之前收到的数据可以被丢弃。
如果一个数据需要多次发送，那么给定的offset不得改变，
否则终端**可以**将同一流中有相同offset但内容
不同的该次接收视为PROTOCOL_VIOLATION类型的连接错误。

流是一种有序的字节流抽象，没有其他
QUIC可见的结构。当数据传输，因丢包而重传，或者送达到
应用层的接受者的时候，STREAM帧边界不会被保留

终端**禁止**在任何未确认通信双方已建立流量
控制的流中发送数据。流量控制将在第4节中详细描述。


## 流的优先级(Stream Prioritization)

如果分配给流的资源优先级正确，流的多路复用可以对应用性能
产生重大影响。

QUIC不提供交换优先级信息的帧。 相反，
它依赖于从使用QUIC的应用程序中获取优先级信息 。

QUIC实现**应该**提供给应用程序可以
表示流的相对优先级的方式。实现**应该**使用
应用提供的信息来决定为哪个
流分配资源，

# 流状态(stream-states)

本节介绍流的发送和接收组件。
描述了两种状态机：
一种用于终端传输数据的流传输状态
({{stream-send-states}})，
另一种是用于终端接收数据的流接收状态
({{stream-recv-states}})。

单向流直接使用适用的状态机。
双向流使用两个状态机。
大部分情况下，无论流是单向的还是双向的，
这些状态机的用法都是相同的。
对于双向流来说，打开流的情况稍微复杂一点，
因为无论是在发送方还是接收方的打开过程
都会让流在两个方向上打开。

一个终端再打开相同类型的流的时候
**必须**使用增序的流传输ID。

注意：
: 这些状态很大程度上是指导性的。
本文档使用流状态来描述何时以及如何
发送不同类型的帧的规则，
以及在接收到不同类型的帧的预期响应规则。
尽管这些这些状态机在实现QUIC时是有用的，
但这些状态并不用于约束实现。
在实现中可以定义不同的状态机，
只要它的行为与实现这些状态的实现的一致。


## 发送流数据的状态 (Sending Stream States) {#stream-send-states}

{{fig-stream-send-states}} 展示了发送数据到对端部分的流的状态

~~~
       o
       | 创建流 (发送)
       | 对端创建双向流
       v
   +-------+
   | Ready | 发送 RESET_STREAM
   |       |-----------------------.
   +-------+                       |
       |                           |
       | 发送 STREAM /              |
       |     STREAM_DATA_BLOCKED   |
       |                           |
       | 对端创建                    |
       |      双向流                |
       v                           |
   +-------+                       |
   | Send  | 发送 RESET_STREAM      |
   |       |---------------------->|
   +-------+                       |
       |                           |
       | 发送 STREAM + FIN          |
       v                           v
   +-------+                   +-------+
   | Data  | 发送 RESET_STREAM  | Reset |
   | Sent  |------------------>| Sent  |
   +-------+                   +-------+
       |                           |
       | 接收 All ACKs              | 接收 ACK
       v                           v
   +-------+                   +-------+
   | Data  |                   | Reset |
   | Recvd |                   | Recvd |
   +-------+                   +-------+
~~~
{: #fig-stream-send-states title="流发送部分的状态"}

终端发起的流的发送部分
（客户端是类型0和2，服务端是类型1和3）
由应用程序打开。“Ready”状态表示一个新创建的流，
该流能够接受来自应用程序的数据。
流数据可以在这种状态下进行缓冲，为发送作准备。

发送第一个STREAM或STREAM_DATA_BLOCKED帧
会导致流的发送部分进入“Send”状态。
一个实现可能直到它发送第一个帧并且进入"Send"状态之后，
选择把流ID分配给流，
这样可以实现更好的流优先级。

对端发起的双向流的发送部分
（服务端是类型0，客户端是类型1）
进入“Ready”状态，然后如果接收部分进入“Recv”状态
（{{stream-recv-states}}）时立刻转换到“Send”状态。

在“Send”状态，
终端以STREAM帧的方式传输，
并在必要时重新传输流数据。
终端遵循对端设置的流量控制，
并且继续接收和处理MAX_STREAM_DATA帧。
一个处于“Send”状态的终端在流发送过程被阻塞
或受到流量控制的时候生成
STREAM_DATA_BLOCKED{{data-flow-control}}帧。

当应用程序指示所有的流数据已经发送，
并且发送了包含FIN位的STREAM帧后，
流发送部分进入“Data Sent”状态。
在这个状态，终端只会在必要的时候重新传输流数据。
终端不用检查流控制限制，也不需要为处于这种状态的流
发送STREAM_DATA_BLOCKED帧。
当对端收到最终的流偏移量之后终端可能会收到
MAX_STREAM_DATA帧。
在这种状态下，
终端可以安全地忽略从对端接收到的任何MAX_STREAM_DATA帧。

一旦所有的流数据都被成功的确认，
流发送部分进入被称为“Data Recvd”的最终状态。

应用程序可以从任何“Ready”，“Send”或“Data Sent”状态
发出希望放弃流数据传输的信号。
或者，终端**可能**从对端收到一个STOP_SENDING帧。
在两种情况下，终端发送RESET_STREAM帧，
这将导致流进入“Reset Sent”状态。

一个终端 **可能** 会将RESET_STREAM做为流发送的第一个帧；
这导致流发送部分打开并立刻进入“Reset Sent”状态。

一旦一个包含RESET_STREAM的包被确认，
流发送部分进入被称为“Reset Recvd”的最终状态。


## 接收流的状态(Receiving Stream States) {#stream-recv-states}

{{fig-stream-recv-states}} 展示了流从对端接收数据部分的状态
。流接收部分的状态只反映了部分对端发送时的状态。
流的接收部分不会跟踪发送部分无法观察的状态，
例如 ‘Ready’（准备）状态。
相反，流的接收部分会跟踪传递给应用的数据送达状态，
其中一部分是发送方无法观察到的。

~~~
       o
       | 接收Recv STREAM(接收流) / STREAM_DATA_BLOCKED(流数据阻塞)/ RESET_STREAM(重置流)
       | 创建双向传输流(发送)
       | 接收 MAX_STREAM_DATA (最大流数据) / STOP_SENDING（停止发送）(双向传输流限定)
       | 创建更高编号的流
       v
   +-------+
   | Recv  | 接收 RESET_STREAM （重置流）
   |       |-----------------------.
   +-------+                       |
       |                           |
       | 接收 STREAM +  FIN        |
       v                           |
   +-------+                       |
   | Size  | 接收  RESET_STREAM    |
   | Known |---------------------->|
   +-------+                       |
       |                           |
       | 接收所有数据               |
       v                           v
   +-------+ 接收 RESET_STREAM +-------+
   | Data  |---   (可能)   --->| Reset |
   | Recvd |     接收所有数据   | Recvd |
   +-------+<--   (可能)   ----+-------+
       |                           |
       | 应用读取所有数据           | 应用读取RST
       v                           v
   +-------+                   +-------+
   | Data  |                   | Reset |
   | Read  |                   | Read  |
   +-------+                   +-------+
~~~
{: #fig-stream-recv-states title="流接收部分的状态"}

由对端（客户端的类型是1和3，服务端的类型是0和2）
发起的流的接收部分在接收到该流的第一个 STREAM，
STREAM_DATA_BLOCKED,或RESET_STREAM时完成创建。
对于由对端发起的双向传输流，接收到由流
的发送部分发出的MAX_STREAM_DATA或STOP_SENDING帧
时也会创建接收部分。
流的接收部分初始状态是“Recv”(接收)。

当终端（客户端是类型0，服务端是类型1）发起的双向传输流
的发送部分进入“就绪”状态时，
流的接收部分进入“Recv”状态。

终端在收到来自流的对端发出的MAX_STREAM_DATA或者
STOP_SENDING帧时打开一条双向传输流。
接收到未开启的流的MAX_STREAM_DATA帧表明远程对端
已经开启了这个流并且正在提供流量控制的信用值
（基于信用的流量控制方式（credit- based flow control））。
接收到未开启的流的STOP_SENDING帧表明远程对端
不再希望在这个流上接收数据。
如果包被丢失或被重排，
两种帧都可能在STREAM或者STREAM_DATA_BLOCKED帧前抵达终端。

在创建一个流前，
所有更低编号的同类型流都**必须**创建完毕。
这保证了流的创建顺序在两端是一致的。

在“Recv”（接收）状态下，
终端接收STREAM和STREAM_DATA_BLOCKED帧。
传入的数据会被缓存起来并重新以正确的顺序组
装起来，以便交付给应用。随着数据被应用消耗，
缓存空间变得可用，终端会发送MAX_STREAM_DATA帧
以允许对端发送更多的数据。

当接收到一个带有FIN标志位的STREAM帧时，
流的最终大小就已知了（详见 {{final-size}}）。
然后流的接收部分就进入“Size Known”（大小已知）状态。
在这个状态下，终端不再需要发送MAX_STREAM_DATA帧，
只接收任何重传的流数据。


一旦收到流的所有数据，流的接收部分就进入
“Data Recvd”（数据已接收）状态。
这可能是因为接收到相同的STREAM帧，导致“Size Known”
（大小已知)的转换
在这个状态下，终端拥有所有的流数据。
从这个流接收到的 STREAM或STREAM_DATA_BLOCKED 帧都可能被丢弃。

“Data Recvd”（数据已接收）状态会持续到
所有流数据都交付给应用。
一旦流数据传输完成，
流会进入 “Data Read”（读取数据）这个终点状态。

在“Recv”(接收)或者“Size Known”（大小已知）状态下接收
RESET_STREAM帧会使流进入“Rest Recvd”（收到重置）状态。
这可能中断交付流数据到应用。

存在收到所有流数据后收到RESET_STREAM帧
的可能（在“Data Recvd”状态）。
同样也存在收到RESET_STREAM帧后还有剩余流数据
到达（在“Reset Recvd”状态）。
实现可以按照它的选择处理这种情况。
发送RESET_STREAM意味着一个终端不能保证流数据的传输。
但是没有要求终端收到RESET_STREAM后不传输数据。
实现**可能**中断流数据的传输，
抛弃任何未被消费的数据并立刻示意收到RESET_STREAM。
或者，当流数据已经完全收到和缓存起来准备被应用读取时
RESET_STREAM信号可能被抑制或者扣留。
在后面这种情况下，
流的接收部分会从“Reset Recvd”转变为“Data Recvd”。

当应用收到流已重置的信号，流的接收部分会过渡到
“Reset Read”（重置已读）这个终点状态。


## 允许的帧类型(Permitted Frame Types)

流的发送者只发送三种会影响发送者和接收者的流状态
的帧类型：分别为STREAM ({{frame-stream}})，
STREAM_DATA_BLOCKED
， RESET_STREAM({{frame-reset-stream}})。

发送者**禁止**在终结状态 ("Data Recvd"
或者 "Reset Recvd") 发送上面的三种帧类型。
发送者**禁止**在发送一个RESET_STREAM后
发送STREAM或者STREAM_DATA_BLOCKED。
这指的是在终止状态和"重置发送(Reset Sent)"状态。
接收者可以在任何状态下接收任何这三种帧类型，
这是因为带着它们的包存在延迟抵达的可能性。

流的接收者发送MAX_STREAM_DATA({{frame-max-stream-data}})
和STOP_SENDING ({{frame-stop-sending}}).

接收者只有在“Recv”状态发送MAX_STREAM_DATA。
在没有接收到一个RESET_STREAM的任意一个状态下，
接收者可以发送STOP_SENDING。
这是不同于 "Reset Recvd" 或者 "Reset Read" 的状态。
但是在“Data Recvd”状态传输一个
STOP_SENDING是没有意义的，
因为所有的流数据都已经被接收了。
发送者可以在包延迟抵达的情况下
接收这两个帧的任何一个。


## 双向流状态(Bidirectional Stream States) {#stream-bidi-states}

双向流由发送和接收部分组成。
实现中**可以**将发送和接收流的状态
作为依据表示双向流的状态。
最简单的模型是当发送或接收部分
处于非终止状态时将流表示为“开放”，
当发送和接收流都处于终结状态时，将流表示为“关闭”。

{{stream-bidi-mapping}} 展示了一个更加复杂的与HTTP/2
{{?HTTP2=RFC7540}} 中的流状态松散对应的双向流状态的映射表。
这表明发送或接收部分流的
多个状态被映射到相同的复合状态。
请注意，这只是这种映射的一种可能性;
此映射要求在转换到“closed”
或“half-closed”状态之前确认数据。

| Sending Part           | Receiving Part         | Composite State      |
|:-----------------------|:-----------------------|:---------------------|
| No Stream/Ready        | No Stream/Recv *1      | idle                 |
| Ready/Send/Data Sent   | Recv/Size Known        | open                 |
| Ready/Send/Data Sent   | Data Recvd/Data Read   | half-closed (remote) |
| Ready/Send/Data Sent   | Reset Recvd/Reset Read | half-closed (remote) |
| Data Recvd             | Recv/Size Known        | half-closed (local)  |
| Reset Sent/Reset Recvd | Recv/Size Known        | half-closed (local)  |
| Reset Sent/Reset Recvd | Data Recvd/Data Read   | closed               |
| Reset Sent/Reset Recvd | Reset Recvd/Reset Read | closed               |
| Data Recvd             | Data Recvd/Data Read   | closed               |
| Data Recvd             | Reset Recvd/Reset Read | closed               |
{: #stream-bidi-mapping title="HTTP/2流状态的可能映射"}

注 (*1):

: 还没有被创建的流，或者流的接收部分在“Recv”
状态中没有收到任何帧，将被视为“空闲(idle)”状态。


## 请求的状态转换(solicited-state-transitions)

如果终端不再对它在流上接收的数据感兴趣，
它**可以**发送一个STOP_SENDING来
标识该流，以推动对端关闭流。
通常表示接收应用程序不再读取它从流中接收的数据
，但这不是传入的数据将被忽略的保证。

发送STOP_SENDING后收到的STREAM
仍计入连接和流的流量控制，即使这些帧在接收时将被丢弃。

一个STOP_SENDING请求接收端发送RESET_STREAM帧。
如果流处于就绪或发送状态，
则接收STOP_SENDING帧的终端**必须**发送RESET_STREAM帧。
如果流处于数据发送状态并且任何未完成的数据被声明丢失
，则终端应该发送RESET_STREAM帧代替重传。

终端应该将错误代码从STOP_SENDING帧
复制到它发送的RESET_STREAM帧，
但是**可以**使用任何应用程序错误代码。
发送STOP_SENDING帧的终端**可以**忽略它接收的
任何RESET_STREAM帧中携带的错误代码。

如果在已经处于“已发送数据(Data Sent)”状态的流上
接收到STOP_SENDING帧，则希望停止在该流上重传先前
发送的STREAM帧的终端**必须**首先发送RESET_STREAM帧。

STOP_SENDING 应该仅针对未被对方重置的流发送。
STOP_SENDING对于“Recv”或“Size Known”状态的流最有用。

如果包含先前STOP_SENDING帧的包已经丢失，
终端应该发送另一个新的STOP_SENDING帧。
但是，一旦为流接收到所有流数据或RESET_STREAM帧 -
也就是说，流处于“Recv”或“Size Known”以外的任何状态 -
发送STOP_SENDING帧是不必要的。

希望断开双向流的终端，可以通过发送一个
RESET_STREAM帧来终止一个方向，
并且它可以通过发送STOP_SENDING帧
来鼓励相反方向的快速终止。


# 流量控制(Flow Control) {#flow-control}

需要对接收方的数据缓冲大小限制，
从而避免快速发送方碾压慢速接收方及
恶意发送者大量消耗接收方内存的情况。
为了使接收方能够将内存开销限制在一个连接上，
并对发送方施加反压力，流是单独控制的，
也可以作为一个聚合来控制。
QUIC接收方可以随时控制发送方在流上发送的最大数据量,
如 {{data-flow-control}} 和
{{fc-credit}}所述。

同样，为了限制连接内的并发，
QUIC终端控制其对端可以发起的最大累计数据流数,
如{{controlling-concurrency}}所述。

在CRYPTO帧中发送的数据不像流数据那样受到流控制。
QUIC依赖于密码协议实现来避免数据的过度缓冲，
请参见{{QUIC-TLS}}。
该实现应该为QUIC提供一个接口，
告诉它的缓冲限制，以便在多个层上不会有过多的缓冲。


## 数据流控制(Data Flow Control) {#data-flow-control}

QUIC采用类似于HTTP/2{{?HTTP2}}中的基于信用的流量控制方案，
在该方案中，
接收方设定它准备在给定流上和整个连接上接收的字节数，
这也是QUIC中的两种数据流控制：

* 流的流量控制，通过限制在任何流上发送的数据量，
防止单个流占用连接的整个接收缓冲区。

* 连接的流量控制，通过限制所有流在STREAM帧中发送的
流数据的总字节数，
防止接收方用于连接的缓冲区容量被发送端消耗殆尽。

接收方通过在握手期间发送传输参数来设置所有流
的初始信用({{transport-parameters}})。
 接收方向发送方发送MAX_STREAM_DATA
 ({{frame-max-stream-data}}) 或MAX_DATA
 ({{frame-max-data}})帧，以通告额外信用。

接收方通过适当发送设置了流ID字段的
MAX_STREAM_DATA帧来通告流的信用。
MAX_STREAM_DATA帧设置流的最大绝对字节偏移量。
接收方可以使用数据消费的当前偏移量来确定
要通告的流量控制偏移量。
接收方可以在多个数据包中发送MAX_STREAM_DATA帧，
以确保发送方在流控制信用用完之前收到更新，
即使其中一个数据包丢失也是如此。

接收方通过发送MAX_DATA帧来通告连接的信用，
该帧指示所有流的绝对字节偏移量之和的最大值。
接收方维护在所有流上接收的字节之和，
用于检查是否违反流控制。
接收方可以使用在所有流上消耗的字节总和来确定
要通告的最大数据限制。

接收方可以通过在连接期间随时发送MAX_STREAM_DATA
或MAX_DATA帧来通告较大的偏移量。
然而，接收方不能违背自己发送的通告。
也就是说，一旦接收方通告了一个偏移量，
它可能通告一个较小的偏移量，但是没效果。

如果发送方违反已通告的连接或流的数据限制，
接收方必须关闭连接并返回FLOW_CONTROL_ERROR
错误({{error-handling}})。

发送方必须忽略任何不会增加流控制限制的
MAX_STREAM_DATA或MAX_DATA帧。

如果发送方超出了流控制信用，它将无法发送新数据，
并被禁止。如果发送方有被流控制限制阻止写入的数据，
应发送STREAM_DATA_BLOCKED或DATA_BLOCKED帧。
在常见情况下，不建议频繁发送这些帧。
如果是调试和监控则另当别论。

发送方仅在数据限制时发送单个
STREAM_DATA_BLOCKED或DATA_BLOCKED帧一次。
除非确定原始帧丢失，
发送方不应发送具有相同数据限制的
多个STREAM_DATA_BLOCKED或DATA_BLOCKED帧。
增加数据限制后，
可以发送另一个STREAM_DATA_BLOCKED或DATA_BLOCKED帧。


## 流信用增量(Flow Credit Increments) {#fc-credit}

本文档把MAX_STREAM_DATA或MAX_DATA帧中通告的
时间和字节数留给实现，但需要了解一些注意事项。
这些特殊帧会增加连接开销。
因此，经常发送小更改的帧是不可取的。
同时，如果更新频率较低，
则需要对限制进行更大的增量，以避免阻塞，
这需要接收方做出更大的资源承诺。
因此，在确定公布的限制有多大时，
在资源承诺和间接费用之间存在权衡。

接收方可以使用自动调优机制基于往返时间估计和接收
应用程序消耗数据的速率来调整通告的
附加信用的频率和数量，
这与常见的TCP实现类似。作为一种优化，
仅当有其他帧要发送或对等设备被阻止时，
才发送与流量控制相关的帧，
以确保流量控制不会导致发送额外的数据包。

如果发送方超出了流控制信用，
它将无法发送新数据并被认为被阻止。
一般认为，最好不要让发送方被阻止。
为了避免阻塞发送方，并合理地考虑丢失的可能性，
接收方应在期望发送方被阻止之前至少
发送两次MAX_DATA或MAX_STREAM_DATA帧。

接收方在发送MAX_STREAM_DATA或MAX_DATA之前，
不能等待STREAM_DATA_BLOCKED或DATA_BLOCKED帧，
因为这样做将意味着发送方至少在整个往返过程中被阻止，
如果对等设备选择不发送STREAM_DATA_BLOCKED或DATA_BLOCKED帧，
则可能会阻塞更长的时间。


## 流终止处理(Handling Stream Cancellation) {#stream-cancellation}

接受两端最终需要就已消耗的流量控制
信用的数量达成一致，
以避免超出流量控制限制或出现死锁。

收到RESET_STREAM帧后，
终端将关闭匹配流的状态，
并忽略到达该流的其他数据。
如果RESET_STREAM帧与同一流的流数据一起重新排序，
则接收方对该流上接收到的字节数的估计可能低于
发送方对发送的字节数的估计。
因此，这两个终端在连接流控制的字节数上可能不一致。

这个问题通过RESET_STREAM帧({{frame-reset-stream}})
设置在流上发送的数据的最终大小来解决。
在接收RESET_STREAM帧时，
接收方明确知道在RESET_STREAM帧
之前在该流上发送了多少字节，
并且接收方必须使用流的最终大小来计算
在其连接级别流控制器中发送的流上的所有字节。

RESET_STREAM突然终止流的一个方向。
对于双向流，
RESET_STREAM对相反方向的数据流没有影响。
两个终端都必须在未终止的方向上保持流的流控制状态，
直到该方向进入终止状态，
或者直到其中一个终端发送CONNECTION_CLOSE为止。


## 流最终大小(Stream Final Size) {#final-size}

最终大小是流消费的流量控制的额度。
假设流上的每一个连续的字节都发送一次，
最终大小就是字节发送的数量。
更常见的，这会比发送的最大字节偏移量大一。

对于一个被重置的流，
最终大小会明确的被携带在 RESET_STREAM 帧中。
或者说，最终大小是偏移量加用 FIN 标志位标记的帧的长度。

终端在接收到流进入“Size Known" 或者
”Reset Recvd" 的部分的时候，
将会知道流的最终大小。

终端**禁止**在或超过最终大小后发送数据。

一旦流的最终大小确定了，它就不能再改变。
如果接收到了指示改变流最终大小的
RESET_STREAM 或者 STREAM 帧，
终端**应该**返回 FINAL_SIZE_ERROR 错误(详见{{error-handling}})。
接收者**应该**对在或超过最终大小的确认
用 FINAL_SIZE_ERROR 错误进行处理，
即使是在流已经关闭的情况下。
生成这些错误不是强制的，
但是这只是因为要求终端生成这些错误也意味着终端
对关闭的流也需要维护最终大小的状态，
这可能意味着严重的状态维持花销。

## Controlling Concurrency {#controlling-concurrency}

终端限制了对端能发起的流的数量。
只有带着流 ID 小于
`(max_stream * 4 + initial_stream_id_for_type)`
才可以以被发起。(详见{{long-packet-types}})。
初始限制在传输参数中设置
(详见{{transport-parameter-definitions}}），
随后限制通过使用 MAX_STREAMS 帧进行建议调整。
单向流与双向流应用相互独立的限制。

终端**禁止**超过对端设置的限制。
终端接收带有超过它已经发送的限制的流 ID 的 STREAM 帧，
**必须**用一个 STREAM_LIMIT_ERROR({{error-handling}})
种类的异常进行处理。

接收者不能违背建议者。
这是说，一旦接收者使用 MAX_STREAMS 帧建议了流上限，
建议一个更小的限制没有任何效果。
接收者**必须**无视任何不增加流上限的 MAX_STREAMS 帧。

关于流与连接流量控制，
这篇文档留下了何时以及如何实现
许多流通过 MAX_STREAMS 帧建议对端的问题。
实现上可能选择当可用流数量接近保持与对端粗
略一致的时候增加上限。

因为对端的限制不能打开一个新的流的终端**应该**
发送一个 STREAMS_BLOCKED 帧{{frame-streams-blocked}}。
这个信号在 debug 的时候很有用。
终端**禁止**在建议额外的额度之前等待接收这个信号，
因为这么做将会意味着对端将会阻塞至少一整个往返周期，
而且如果对端选择不发送 STREAMS_BLOCKED 帧可能更长。

# 连接(Connections) {#connections}

如 {{handshake}}所述，QUIC 的连接建立将版本协商与加密、
传输握手结合以减少连接建立延迟。连接一旦建立，就
可以迁移到任一终端上的不同 IP 或端口，详细
说明在{{migration}}。最后，如 {{termination}}所述，
连接可被任一终端终止。

## 连接 ID(Connection ID) {#connection-id}

每个连接都有一组连接标识符或连接 ID，每个标识符或 ID 都
可以标识连接。连接 ID 由终端独立选择，
每个终端选择其对端使用的连接 ID。

连接 ID 的主要功能是确保较低协议层（UDP，IP）的寻址
改变不会导致 QUIC 连接的包被传递到错误的终端。每个终端
使用特定于实现的（也可能是特定于部署的）方法选择
连接 ID 该方法将允许具有该连接 ID 的包被路由
回该终端，并在收到时由该终端标识。

连接 ID**禁止**包含任何可由外部观察者用于将其与
同一连接的其他连接 ID 相关联的信息。作为一个简单的
示例，这意味着同一个连接中**禁止**多次发出同一个
连接 ID。

具有长头部的包包括源连接 ID 和目标连接 ID 字段。
这些字段用于设置新连接的连接 ID，有关详细信息，
请参见 {{negotiating-connection-ids}}。

具有短头部的包({{short-header}})仅包含目标
连接 ID 并忽略显式长度。目标连接 ID 字段的长度应该是所有
终端都知道的。使用基于终端连接 ID 进行
路由的负载均衡器的终端也可以使用固定长度或确定
编码方案的连接 ID 的负载平衡器。固定部分可以
对显式长度进行编码，从而允许整个连接 ID 的长度
各不相同，并且仍然可被负载平衡器使用。

版本协商({{packet-version}}) 包回显客户端选择
的连接 ID，以确保到客户端的路由正确，并允许客户端
验证包是否响应初始包。

当路由不需要连接 ID 且包的地址/端口元组足以识别
连接时，**可以**使用零长度连接 ID。一个对端已
选择零长度连接 ID 的终端在连接生存期内**必须**（MUST）
继续使用零长度连接 ID，并且**禁止**发送从任何
其他本地地址收到的包。

当一个终端请求了一个非 0 长度的连接 ID，这个终端
需要确保对端有充足的连接 ID 供发送返回到终端的
包使用。这些连接 ID 由使用 NEW_CONNECTION_ID 帧
的终端提供 ({{frame-new-connection-id}})。

### 发布连接 ID（Issuing Connection IDs） {#issue-cid}

每个连接 ID 都有一个关联的序列号，以帮助消除重复消息。
在握手过程中终端发布的初始连接 ID 会在
长包头部({{long-header}})的源连接 ID 字段中
发送出去。初始连接 ID 的序列号是 0。如果
发送了 preferred_address
（首选地址）传输参数，则提供的连接 ID 的序列号为 1。

附加连接 ID 通过 NEW_CONNECTION_ID 帧被传送给
对端({{frame-new-connection-id}})。 每个新发布的
连接 ID 上的序列号**必须**增加 1。除非服务器
选择保留初始连接 ID，否则不会为客户端在初始包中
随机选择的连接 ID 和重试包提供的任何连接 ID
分配序列号。

当终端分配了一个连接 ID 时，它**必须**接受
在连接期间携带此连接 ID 的包，或者直到其对端通过
RETIRE_CONNECTION_ID 帧使连接 ID 无效({{frame-retire-connection-id}})。

终端存储已接收的连接 ID 以供将来使用。
接收过多连接 ID 的终端**可能**在
不发送 RETIRE_CONNECTION_ID帧的情况下丢弃
那些无法存储的连接 ID。 发布了连接 ID 的终端
不能指望其对端存储和使用所有已发布的连接 ID。

终端**应该**确保其对端具有足够数量的
可用和未使用的连接 ID。 虽然每个终端独立选择要发布的
连接 ID 数，但终端**应该**提供并维护
至少八个连接 ID。 为此，终端**应该**通过
在对端收回某个连接 ID 时或者当终端接收到具有先前
未使用的连接 ID 的包时始终提供新的连接 ID。 发起迁移
并要求非零长度连接 ID 的终端**应该**在
迁移之前为其对端提供新的连接 ID，否则可能会使对端
关闭连接。

### 消费和收回连接ID(Consuming & Retiring Connection IDs {#retiring-cids}

终端可以在连接期间随时将其用于对端的连接 ID 更改为
另一个可用的连接 ID。 终端消费连接 ID 以响应
迁移中的对端，有关更多信息，参见 {{migration-linkability}} 。

终端维护从对端接收的一组连接 ID，在发送包时可以使用
其中的任何一个连接 ID。 当终端希望移除使用中的
连接 ID 时，它会向其对端发送 RETIRE_CONNECTION_ID 帧。
发送一个 RETIRE_CONNECTION_ID 帧表示当前连接 ID 将
不再使用，并且使用 NEW_CONNECTION_ID 帧请求对端将
当前连接 ID 替换为新的连接 ID。

如{{migration-linkability}}所述，每个连接 ID**必须**只
用于从一个本地地址发送的包。从本地地址迁移的终端在
不再计划使用该地址后，应停用该地址上使用的
所有连接 ID。

## 包匹配至连接(Matching Packets to Connections) {#packet-handling}

传入的数据包在接受时会被分类。
数据包可以关联至现有连接，
或者也可能（对于服务器）创建新连接。

主机会尝试将数据包关联至现有连接。
如果数据包有与现有连接相对应的目标连接ID，
则QUIC会以此处理该数据包。
请注意，可以将多个连接ID与一个连接关联{{connection-id}}。

如果目标连接ID为零长度，
且数据包匹配的地址或端口是主机不需要链接ID的链接，
则QUIC会将该数据包作为上述连接的一部分进行处理。
终端**应该**拒绝以下操作以确保数据包正确地匹配连接：

* 使用与现有连接相同的地址的连接尝试。

* 使用非零长度的目标连接ID。

终端可以为任何无法匹配现有连接的数据包
发送无状态重置（{{stateless-reset}}）。
无状态重置允许对端更快地识别连接何时变得不可用。

如果数据包与该连接的状态不一致，
则丢弃该数据包（即使它已经与现有连接匹配）。
例如，当数据包指示的协议版本与连接的协议版本不同，
或者所需密钥可用后数据包解密不成功时，
该数据包将会被丢弃。

未加密的无效数据包，
例如初始化，重试或版本协商包**可以**被丢弃。
如果终端在发现错误之前有提交状态更改，
则它**必须**生成一个连接错误。


### 客户端包处理(Client Packet Handling) {#client-pkt-handling}

发送到客户端的有效数据包始终包含与
客户端选择的值匹配的目标连接ID。
选择接收零长度连接ID的客户端可以使用
地址/端口元组来识别连接。
与现有连接不匹配的数据包将被丢弃。

由于数据包重排或丢失，
客户端可能会收到使用尚未计算的密钥加密的连接数据包。
客户端**可以**丢弃这些数据包，
也**可以**缓存它们以期待于后续的包会允许它计算出密钥。
如果客户端收到的数据包包含不受支持的版本，
则**必须**丢弃该数据包。


### 服务器包处理(Server Packet Handling) {#server-pkt-handling}

如果服务器收到的数据包包含不受支持的版本，
但数据包太大以至于无法为
服务器支持的任何版本启动新连接，
则**应该**按照{{send-vn}}中的说明发送版本协商数据包。
服务器可以对这些数据包进行速率控制，
以避免产生版本协商数据包风暴。

不受支持的版本的第一个数据包可以对任何版本特定字段
使用不同的语义和编码。
值得一提的是，
不同的数据包加密密钥可能用于不同的版本。
不支持特定版本的服务器不太可能解密数据包的有效负载。
服务器**不应该**尝试解码或解密来自未知版本的数据包，
而是发送版本协商数据包（前提是数据包足够长）。

服务器**必须**丢弃包含不受支持的版本的其他数据包。

具有受支持版本或无版本字段的数据包
与使用连接ID与连接进行匹配，
具有零长度连接ID的数据包则使用地址元组进行匹配。
如果数据包与现有连接不匹配，则服务器按照下文处理。

如果数据包是完全符合规范的初始化数据包，
则服务器继续握手（{{handshake}}）。
这向服务器申明了客户端选择的版本。

如果服务器当前没有接受任何新连接，
它**应该**发送一个包含 CONNECTION_CLOSE
帧的初始数据包与错误代码 SERVER_BUSY 。

如果该包是0-RTT包，
则服务器**可以**缓冲有限数量的此类包
并等待延迟的初始数据包。
在接收服务器响应之前，客户端被禁止发送握手数据包，
因此服务器**应该**忽略任何此类握手数据包。

服务器**必须**在所有其他情况下丢弃传入的数据包。


## QUIC连接寿命(Life of a QUIC Connection) {#connection-lifecycle}

待定。

<!-- Goes into how the next few sections are connected. Specifically, one goal
is to combine the address validation section that shows up below with path
validation that shows up later, and explain why these two mechanisms are
required here.

suggested structure:

 - establishment
   - VN
   - Retry
   - Crypto
 - use (include migration)
 - shutdown

-->


# 版本协商(Version Negotiation) {#version-negotiation}

版本协商确保了客户端和服务端对某一个双方同时支持的
QUIC 版本达成了一致。
服务器对每一个初始化新连接的回包中附带了一个版本协
商包，详见{{packet-handling}}。

客户端发送的第一个包的大小将会决定服务器是否发送一
个版本协商包。
支持多个 QUIC 版本的客户端**应该**将第一个包填充
到在它支持的所有版本中最小包大小中的最大值。
这确保了服务端在出现一个同时支持的版本时作出响应。


## 发送版本协商包(Sending Version Negotiation Packets) {#send-vn}

如果客户端选择的版本服务端不支持，
服务端会回复一个版本协商包（详见{{packet-version}}）。
这个包里包括了一个服务端支持的版本列表。
一个终端**禁止**在收到一个版本协商包后发送版本协商包。

系统允许服务端不保持状态的情况下处理不支持版本的包。
无论初始化包或者版本协商包都可能在回包中丢失，
客户端会发送新的包直到它成功收到回复或放弃连接尝试。

服务端**可以**限制它发送的版本协商包数量。
例如，能辨别出包是 0-RTT 的服务端在回复 0-RTT 包的时候
可能选择不发送版本协商包，
因为它认为之后会收到一个初始化包。


## 处理版本协商包(Handling Version Negotiation Packets) {#handle-vn}

当客户端收到了版本协商包，
它**必须**放弃当前的连接尝试。
版本协商包的设计旨在使得终端之间协商出要使用的版本
能允许是 QUIC 未来的版本。
未来版本的QUIC可能会改变建立链接时
多版本支持对版本协商包的回应。
如何做版本协商留待未来版本的 QUIC 定义。
特别是的，未来的工作需要保证
对版本降级攻击{{version-downgrade}}有鲁棒性。


### 草案版本间的版本协商(Version Negotiation Between Draft Versions)

\[\[RFC 编辑者: 请在发布之前删除此章节。]]

当该草案的实现接收了一个版本协商包，
它**可能**使用它包中列举的版本之一来尝试一条新连接，
而不是丢弃当前的连接尝试 {{handle-vn}}。

客户端**必须**检查目标和源连接ID字段
与客户端发送的包中匹配。
如果检查失败，则包**必须**被丢弃。

一但版本协商包决定为有效，
客户端从服务端提供的列表中选择一个可接受的协议版本，
尝试使用此版本创建一条新连接。
新连接**必须**使用一个和之前发送过的不同的
新的随机的目标连接ID。

注意这个机制并不防卫降级攻击
而且**禁止**在草案实现之外使用。


## 使用保留版本(Using Reserved Versions)

对在未来使用新版本的服务端，
客户端必须正确的处理不支持的版本。
为了帮助确保这件事，当生成一个版本协商包时，
服务端**应该**包括一个保留版本（详见{{versions}}）。

版本协商的设计允许服务端用这种方式
避免维护它拒绝的包的状态。

客户端**可能**使用一个保留版本号发送包。
这可能用于索要服务端所支持的版本列表。


# 加密与传输握手(Cryptographic and Transport Handshake) {#handshake}

QUIC使用结合在一起的加密和传输握手来最小化链接建立延迟。QUIC使用CRYPTO帧{{frame-crypto}}
来进行加密握手。0x00000001版本的QUIC使用TLS{{QUIC-TLS}}；不同版本的QUIC可能使用
不同的加密握手协议。

QUIC提供可信的、有序的加密握手数据交付。QUIC数据包保护被用来编码尽可能多的握手协议包。
加密握手**必须**提供如下特性：

* 认证密钥交换，当

  * 服务器总是经过认证的，且

  * 客户端是可能经过认证的，且

  * 每一个链接都产生不同且不相关的密钥，且

  * 密钥可以保护0-RTT和1-RTT的数据包，且

  * 1-RTT的密钥具有前向保密性

* 对端传输参数的认证值（参见{{transport-parameters}}）

* 应用层协议的认证协商（TLS使用ALPN{{?RFC7301}}来达到这个目的）

客户端的第一个CRYPTO帧**必须**被单独放在一个包中发送。任何由地址验证触发的第二次尝试（参见
{{validate-handshake}}）也都**必须**被单独放在一个包中发送。这样可以避免从多个数据包重
新组合消息。

加密握手协议的第一个客户端包**必须**长度小于等于1232个字节的QUIC包负载。这包括减少加密握手
协议可用空间的开销。

终端可以在它发送的第一个数据包中验证对现实用塞通知（ECN）的支持，在{{ecn-verification}}
中介绍。

CRYPTO帧可以在不同的数据包编号空间中发送。CRYPTO帧用来保证加密握手数据顺序交付而使用的序号在
每个数据包序号空间中是从零开始的。

终端**必须**显式的协商应用层协议。这样避免了对正在使用的协议产生分歧的情况。

## 握手流示例(Example Handshake Flows)

{{QUIC-TLS}}中提供了QUIC使用TLS的相关细节，这里提供一些示例。{{validate-retry}}提供了
一个让次交换支持客户端地址验证的拓展。

一旦完成了地址验证，加密握手就被用作协商加密密钥。加密握手在初始(Initial)包
（{{packet-initial}}）和握手(Handshake)包（{{packet-initial}}）中进行。

{{tls-1rtt-handshake}} 提供了有关1-RTT握手的介绍。每一行显示一个QUIC包，首先是包的类型和
序号，接着是通常包含在包中的帧。例如，第一个包类型为序号为0的“初始（Initial）”，其中包含着承载
了ClientHello的CRYPTO帧。

注意，多个QUIC包 -- 甚至是不同加密级别的 -- 也可能被合并到单个UDP数据报中
（参见{{packet-coalesce}}），因此这种握手可能只包含4个UDP数据报，也可能包含更多的数据报。
例如，服务器的第一个数据报包含初始（Initial）加密级别（混淆）的包、握手（Handshake）级别的包
和服务器使1-RTT加密级别的“0.5-RTT数据”。

~~~~
Client                                                  Server

Initial[0]: CRYPTO[CH] ->

                                 Initial[0]: CRYPTO[SH] ACK[0]
                       Handshake[0]: CRYPTO[EE, CERT, CV, FIN]
                                 <- 1-RTT[0]: STREAM[1, "..."]

Initial[1]: ACK[0]
Handshake[0]: CRYPTO[FIN], ACK[0]
1-RTT[0]: STREAM[0, "..."], ACK[0] ->

                            1-RTT[1]: STREAM[3, "..."], ACK[0]
                                       <- Handshake[1]: ACK[0]
~~~~
{: #tls-1rtt-handshake title="1-RTT 握手（Handshake）的示例"}

{{tls-0rtt-handshake}}展示了包含0-RTT握手和单个0-RTT数据包的链接示例。注意，就和
{{packet-numbers}}中描述的一样，服务端在1-RTT加密级别确认0-RTT数据，客户端在相同的包编号
空间发送1-RTT包。

~~~~
Client                                                  Server

Initial[0]: CRYPTO[CH]
0-RTT[0]: STREAM[0, "..."] ->

                                 Initial[0]: CRYPTO[SH] ACK[0]
                        Handshake[0] CRYPTO[EE, CERT, CV, FIN]
                          <- 1-RTT[0]: STREAM[1, "..."] ACK[0]

Initial[1]: ACK[0]
Handshake[0]: CRYPTO[FIN], ACK[0]
1-RTT[1]: STREAM[0, "..."] ACK[0] ->

                            1-RTT[1]: STREAM[3, "..."], ACK[1]
                                       <- Handshake[1]: ACK[0]
~~~~
{: #tls-0rtt-handshake title="0-RTT 握手（Handshake）的示例"}


## 协商连接IDs （Negotiating Connection IDs） {#negotiating-connection-ids}

连接ID用来确保数据包的路由一致性，如 {{connection-id}} 所述。
长标题包含两种连接ID：目标连接ID是由接收包选中的，用于提供一致的路由;
源连接ID用于设置对端使用的目标连接ID。

在握手过程中，使用长报头({{long-header}})的数据包来建立每个终端使用的连接ID。
每个终端使用源连接ID字段指定发送给它们的数据包中目标连接ID字段中使用的连接ID。
在接收到数据包时，每个终端设置它发送的目标连接ID，
以匹配它们接收到的源连接ID的值。

当一个初始数据包由之前没有从服务器接收重试数据包的客户机发送时，
它将用一个不可预知的值填充目标连接ID字段。
它的长度**必须**至少为8字节。
在从服务器接收到数据包之前，客户端**必须**使用相同的值，
除非它放弃连接尝试并启动新的连接。
初始目标连接ID用于确定初始数据包的包保护密钥。

客户端使用其选择的值填充源连接ID字段，并设置SCIL字段来指示长度。

0-RTT数据包的第一次传输使用与客户端第一次初始化相同的目标和源连接ID值。

服务器初始数据包中的目标连接ID字段包含由数据包的接收者(比如客户端)选择的连接ID;
源连接ID包括数据包的发送方希望使用的连接ID(参见 {{connection-id}})。
服务器在握手期间**必须**使用一致的源连接id。

在首次从服务器接收初始或重试数据包时，
客户端使用服务器提供的源连接ID作为后续数据包(包括任何后续0-RTT数据包)的目标连接ID。
这意味着客户端可能在连接建立期间两次更改目标连接ID，一次是响应重试，
一次是响应来自服务器的第一个初始数据包。
一旦客户端从服务器接收到一个初始数据包，
它**必须**丢弃它接收到的任何具有不同源连接ID的数据包。

客户端**必须**只更改它在目标连接ID中发送的值，
以响应它从服务器接收到的每种类型的第一个数据包(重试或初始);
服务器**必须**根据初始数据包设置其值。不允许有任何其他变更;
如果这些类型的后续数据包包含不同的源连接ID，则它们**必须**被丢弃。
这避免了对产生不同连接ID的多个初始数据包进行无状态处理时可能出现的问题的发生。

连接ID可以在连接的生命周期中更改，
特别是在响应连接迁移时({{migration}})，请参阅{{issue-cid}}了解详细信息。

## 传输参数（Transport Parameters） {#transport-parameters}

在连接建立期间，两个终端对其传输参数进行身份验证声明。
这些声明是由每个终端单方面作出的。
终端必须遵守这些参数隐含的限制;每个参数的描述包括它的处理规则。

传输参数的编码详见{{transport-parameter-encoding}}。

QUIC包含加密握手中的已编码传输参数。一旦握手完成，对端声明的传输参数就可用了。
每个终端验证其对端提供的值。

每个定义的传输参数的定义都包含在{{transport-parameter-definitions}}中。
终端**必须**将接收到的具有无效值的传输参数视为
类型为TRANSPORT_PARAMETER_ERROR的连接错误。
在给定的传输参数扩展中，任何给定的参数最多只能出现一次。
终端**必须**将接收到的重复传输参数视为
类型为TRANSPORT_PARAMETER_ERROR的连接错误。

如果服务器发送了一个重试包来启用重试的验证，
如{{packet-retry}}所述，那么它**必须**包含original_connection_id传输参数
({{transport-parameter-definitions}})，

### 0-RTT的传输参数值（Values of Transport Parameters for 0-RTT） {#zerortt-parameters}

尝试发送0-RTT数据的客户端**必须**记住服务器使用的传输参数。
服务器在建立连接期间声明的传输参数适用于由握手期间建立的密钥内容恢复的所有连接。
已记忆的传输参数将应用于新连接，直至握手完成，并且可以提供来自服务器的新传输参数的时候。

服务器可以记住它所声明的传输参数，
或者存储在票据中受完整性保护的值的副本，并在接受0-RTT数据时恢复信息。
服务器使用传输参数来决定是否接受0-RTT数据。

服务器**可以**接受0-RTT，然后为新连接中使用的传输参数提供不同的值。
如果服务器接受0-RTT数据，则服务器**不能**减少任何限制，
也不能更改携带0-RTT数据的客户端可能违反的任何值。
特别是，接受0-RTT数据的服务器**不能**
为以下参数({{transport-parameter-definitions}}) 设置小于这些参数已存储的值。

* initial_max_data
* initial_max_stream_data_bidi_local
* initial_max_stream_data_bidi_remote
* initial_max_stream_data_uni
* initial_max_streams_bidi
* initial_max_streams_uni

省略或设置某些传输参数的零值可能导致启用0-RTT数据，但不可用。
对于0-RTT，允许发送应用程序数据的传输参数的适用子集**应该**设置为非零值。
这包括initial_max_data和initial_max_streams_bidi和
initial_max_stream_data_bidi_remote，或者initial_max_streams_uni
和initial_max_stream_data_uni。

在建立新连接时，**不能**使用服务器上一个的preferred_address的值;
相反，客户机应该等待观察在握手时服务器的preferred_address新值。

如果传输参数的隐含值不受支持，服务器**必须**要么拒绝0-RTT数据，要么中止握手。

### 新的传输参数（New Transport Parameters）

新的传输参数可以用来协商新的协议行为。终端**必须**忽略它不支持的传输参数。
因此，传输参数的缺少将禁用使用该参数协商的任何可选协议的特性。

可以根据{{iana-transport-parameters}}中的规则注册新的传输参数。


# 地址验证(Address Validation) {#address-validation}

QUIC使用地址验证来避免被用于流量放大攻击。
在这样的攻击中，带有伪装成受害者源地址信息
的数据包被发送到服务器。
如果服务器生成更多或更大的数据包作为对该数据包的响应，
攻击者
可以使用该服务器向受害者发送超出其能力的更多的数据。

针对放大攻击的主要防御措施是验证端点是否
能够在其声称的传输地址接收数据包。地址验证在
连接建立期间(see {{validate-handshake}})
和连接迁移期间 (see {{migrate-validate}})执行。


## 连接建立过程中的地址验证(Address Validation During Connection Establishment) {#validate-handshake}

连接建立隐式地为两个端点提供地址验证。
具体地说，就是通过接收由握手密钥保护的数据包来
确认客户端从服务器接收到初始数据包。
一旦服务器成功地处理了来自客户端的握手数据包，它
就可以认为客户端地址已经被验证。

在验证客户端地址之前，
服务器发送的字节数**禁止**超过其接收字节数的三倍。
这就限制了任
何通过使用带欺骗性源地址进行的放大攻击的规模。
该限制仅计算服务器已经成功处理的数据包的大小。

客户端**必须**将仅包含初始数据包的UDP数据报填充到至少1200字节。
一旦客户端收到握手数据包的确认，它可能会发送较小的数据报。
发送填充数据报可确保服务器不受放大限制的过度限制。

数据包丢失，特别是来自服务器的握手数据包的丢失，
可能导致当客户端没有数据要发送且达到
抗放大限制时，服务器无法发送。
为了避免造成握手死锁，
客户端**应该**在加密重传超时发送数据包，
如{{QUIC-RECOVERY}}所述。
如果客户端没有要重新传输的数据，并且没有握手密钥，
则**应该**在至少1200字节的UDP数据报中发送初始数据包。
如果客户端有握手密钥，则**应该**发送握手数据包。

服务器可能希望在开始加密握手之前验证客户端地址。
QUIC在完成握手之前使用初始数据包中的
令牌来提供地址验证。
此令牌在使用重传数据包 (see {{validate-retry}}) 建立连接期间或
在使用NEW_TOKEN帧(see {{validate-future}})之前的连接中传递给客户端。

除了地址验证之前施加的发送限制之外，
服务器还受到拥塞控制器设置的限制。客户端仅受拥塞
控制器的约束。


### 使用重试包进行地址验证(Address Validation using Retry Packets) {#validate-retry}

在接收到客户端的初始包后，服务器可以通过发送
包含令牌的重试包({{packet-retry}})来请求
地址验证。客户端在收到重试包后，必须在其发送
的所有初始包中重复此令牌。作为对包含令牌的
初始处理的响应，服务器可以中止连接或允许连接继续。

只要攻击者不可能为其自己的地址生成有效的
令牌(请参见{{token-integrity}})，并且客户端
能够返回该令牌，它就会向服务器证明它收到了令牌。

服务器还可以使用重试包来延迟连接建立的状态和
处理成本。通过为客户端提供不同的连接ID，服务器可以
将连接路由到具有更多可用于新连接的资源的服务器实例。

{{fig-retry}}中有一个展示重试包使用方法的流。


~~~~
客户端                                               服务端

Initial[0]: CRYPTO[CH] ->

                                                <- Retry+Token

Initial+Token[1]: CRYPTO[CH] ->

                                 Initial[0]: CRYPTO[SH] ACK[1]
                       Handshake[0]: CRYPTO[EE, CERT, CV, FIN]
                                 <- 1-RTT[0]: STREAM[1, "..."]
~~~~
{: #fig-retry title="例子 具有重试的握手"}


### 未来连接的地址验证(Address Validation for Future Connections) {#validate-future}

服务器可在一个连接期间向客户端提供地址验证令牌，
该地址验证令牌可用于后续连接。地址验证对于0-RTT
尤为重要，因为服务器可能会向客户端发送大量数据以
响应0-RTT数据。

服务器使用NEW_TOKEN帧{{frame-new-token}}向
客户端提供可用于验证未来的连接的地址验证令牌。客户端
将此令牌包含在初始包中，以便在将来的连接中提供
地址验证。除非重试或NEW_TOKEN帧将令牌替换为较新的令牌，
否则客户端必须在其发送的所有初始包中包含该令牌。
客户端不能为将来的连接使用重试中提供的令牌。服务器
可能会丢弃不携带预期令牌的任何初始包。

与为重试包创建的令牌不同，在创建令牌和随后使用
令牌之间可能会有一段时间。因此，令牌应包括过期时间。
服务器可以包括显式的过期时间或发布的时间戳，并动态地
计算过期时间。在两个不同的连接上，客户端口号也不太
可能相同；因此，验证端口不太可能成功。

应该为服务器构造一个令牌，以便于将其与在同一字段中
传送的重试包中发送的令牌区分开来。

如果客户端在先前的它认为是同一服务器的
连接的NEW_TOKEN帧中接收到令牌，则应在其初始
包的Token字段中包含该值。包含令牌可以让
服务器无需额外的往返验证客户端地址。

令牌允许服务器在发出令牌的连接和使用令牌的
任何连接之间关联活动。希望中断与服务器的身份连续性的
客户端可能会放弃使用NEW_TOKEN帧提供的令牌。在重试包
中获得的令牌必须在连接尝试过程中立即使用，并且
不能在后续连接尝试中使用。

客户端不应在不同的连接中重用令牌。重用令牌允许
通过网络路径上的实体链接
连接(请参见{{migration-linkability}})。
如果客户端认为自上次使用令牌以来其网络附着点
发生了更改，即如果其本地IP地址或网络接口发生了
更改，则不得重用该令牌。如果客户端在完成握手
之前迁移，则需要重新启动连接过程。

当服务器收到带有地址验证令牌的初始包时，
它必须尝试验证该令牌，除非它已经完成了
地址验证。如果令牌无效，则服务器像客户端
没有经过验证的地址一样处理，包括可能发送
重试。如果验证成功，服务器应该允许握手继续。

注：将客户端视为未验证而不是丢弃包的
基本原理是，客户端可能已使用NEW_TOKEN帧
在以前的连接中接收到令牌，如果服务器已丢失
状态，则可能根本无法验证令牌，如果丢弃
包，则会导致连接失败。服务器应该对NEW_TOKEN帧
提供的令牌进行编码，并以不同的方式重试包，
并对后者进行更严格的验证。

无状态设计中，服务器可以使用加密的和经过
身份验证的令牌将信息传递给客户端，然后
服务器可以恢复并使用这些令牌来验证客户端地址。
令牌未集成到加密握手中，因此不会对其进行
身份验证。例如，客户端可能能够重用令牌。为了避免
利用此属性的攻击，服务器可以将其令牌的使用限制
为仅验证客户端地址所需的信息。

攻击者可以重放令牌，以便在DDoS攻击中将服务器
用作放大器。为防止此类攻击，服务器应确保以
重试包发送的令牌仅在短时间内被接受。
NEW_TOKEN帧中提供的令牌(请参见{{frame-new-token}})
需要更长时间有效，但不应在短时间内多次接受。鼓励
服务器在可能的情况下只允许令牌使用一次。

### 地址验证令牌完整性(Address Validation Token Integrity) {#token-integrity}

地址验证令牌必须很难猜测。在令牌中包含
足够大的随机值就足够了，但这取决于服务器
是否记住它发送给客户端的值。

基于令牌的方案允许服务器将与验证关联的
任何状态卸载到客户端。要使此设计正常工作，
必须对令牌进行完整性保护，以防止客户端
修改或伪造令牌。如果没有完整性保护，恶意
客户端可能会生成或猜测服务器将接受的令牌的值。
只有服务器需要访问令牌的完整性保护密钥。

不需要为令牌使用一个定义良好的格式，
因为生成令牌的服务器也会使用它。令牌
可以包含有关声明的客户端地址(IP和端口)的
信息、时间戳以及服务器将来验证令牌所需的任何
其他补充信息。

## 路径验证(Path Validation) {#migrate-validate}

迁移终端在连接迁移(参考{{migration}} 和
{{preferred-address}})期间使用路径验证来验证从新的
本地地址到对端的可达性。在路径验证中，终端测试特定
本地地址与特定对等地址之间的可达性，其中地址是IP
地址和端口的两元组。

路径验证会测试包（PATH_CHALLENGE）从路径上的对端
发送和接收（PATH_RESPONSE）的可行性。更重要的是，
路径验证确认从迁移的对端接收的包不携带欺骗性的
源地址。

任何终端都可以随时使用路径验证。 例如，终端可能会
在一段时间的静默后检查对端是否仍然拥有其地址。

路径验证不是设计为NAT穿透机制。 虽然这里描述的机制
可能对创建支持NAT穿透的NAT绑定有效，但是期望一个或
另一个对端能够在没有先在该路径上发送包的情况下
接收包。有效的NAT穿透需要路径验证没提供的额外
同步机制。

终端**可能**把用于路径验证的PATH_CHALLENGE和
PATH_RESPONSE帧和其他帧进行捆绑。 特别地，终端
可以装配一个携带PATH_CHALLENGE的包用于PMTU探测，
或者终端可以把一个PATH_RESPONSE和自己的
PATH_CHALLENGE捆绑起来。

在探测新路径时，终端可能希望确保其对端具有可用于
响应且未使用的连接ID。 终端可以在同一个包中发送
NEW_CONNECTION_ID和PATH_CHALLENGE帧。 这可
确保在发送响应时，对端有未使用的连接ID可以使用。


## 启动路径验证(Initiating Path Validation)

要启动路径验证，终端会在要验证的路径上发送包含随机
有效负载的PATH_CHALLENGE帧。

终端**可能**发送多个PATH_CHALLENGE帧以防止丢包。
终端**应该不**比初始数据包更频繁地
发送PATH_CHALLENGE，
从而确保连接迁移到新的路径时负载量和建立一个新连接
是一样的。

终端**必须**在每个PATH_CHALLENGE帧中使用
不可预测的数据，以便它可以将对端的响应与相应的
PATH_CHALLENGE相关联。


## 路径验证响应(Path Validation Responses)

在接收到PATH_CHALLENGE帧时，终端**必须**在
PATH_RESPONSE帧中填入PATH_CHALLENGE帧中包含的
数据立刻发回。

为了确保包可以发送到对端和从对端接收，**必须**在与
触发PATH_CHALLENGE相同的路径上发送PATH_RESPONSE。
也就是说，从收到PATH_CHALLENGE的同一本地地址发到
发出这个PATH_CHALLENGE的同一个远程地址。


## 成功的路径验证（Successful Path Validation）

当收到符合以下标准的PATH_RESPONSE帧时，
新地址才被认为是有效的:

- 帧中包含先前PATH_CHALLENGE中发送的数据。
收到对收到包含PATH_CHALLENGE帧的包的确认是不充分的验证，
因为确认可能被恶意对等方欺骗。

- 帧是从发送相应PATH_CHALLENGE的同一远程地址发送的。
如果从与发送PATH_CHALLENGE的远程地址不同的远程地址
接收到PATH_RESPONSE帧，则认为路径验证失败，即使数据
与PATH_CHALLENGE中发送的数据匹配也是如此。

- 帧是在发送相应PATH_CHALLENGE的同一本地地址上收到的。

请注意，在不同的本地地址上接收不会导致路径验证失败，
因为它可能是转发数据包（请参阅{{off-path-forward}}）
或错误路由的结果。 将来可能会收到有效的PATH_RESPONSE。


## 失败的路径验证（Failed Path Validation）

路径验证只在当尝试验证路径的终端放弃其验证路径的
尝试时失败。

终端**应该**放弃基于计时器的路径验证。 设置此
计时器时，协议的实现会警告新路径的往返时间可能
比原始路径长。 建议使用{{QUIC-RECOVERY}}中
定义的当前探测超时（PTO）或初始超时（即2 * kInitialRtt）
中较大者的三倍的值。 就是说：

~~~
   validation_timeout = max(3*PTO, 6*kInitialRtt)
~~~

请注意，终端可能会在新路径上接收包含其他帧的数据包，
但路径验证成功要求收到具有正确数据的PATH_RESPONSE帧。

当终端放弃路径验证时，等于确定该路径不可用。
这并不一定意味着连接失败 - 终端可以继续在适当的情况下
通过其他路径发送数据包。 如果没有可用的路径，
则终端可以等待一个新路径变为可用或关闭连接。

除了失败之外，路径验证也可能因为其他原因被放弃。
这种情况主要发生于如果在旧路径上的路径验证正在
进行时启动到新路径的连接迁移。


# 连接迁移(Connection Migration) {#migration}

使用连接ID允许连接在终端地址（即IP地址和/或端口
改变时存活，例如当终端迁移到新网络时。 本节
介绍终端迁移到新地址的过程。

终端**禁止**在握手完成并且终端具有1-RTT密钥之前
启动连接迁移。QUIC的设计依赖于终端在握手期间保留
稳定的地址。

如果对端在握手期间发送了“disable_migration”传输参数，
则终端也**禁止**启动连接迁移。 已发送此传输参数但
检测到对端仍迁移到其他网络的终端**可能**将此
视为INVALID_MIGRATION类型的连接错误。

并非所有对端地址的更改都需要端迁移。 对端可能
正在进行NAT重新绑定,此时中间件地址的更改（通常是NAT）
给流分配新的传出端口或甚至是新的传出IP地址而导致的地址
更改。 NAT重绑定不是本节中定义的连接迁移，但是如果
终端检测到其对端的IP地址发生更改，则**应该**执行
路径验证（{{migrate-validate}}。

本文档约束了（除{{preferred-address}}中所述之外）
将连接迁移到新客户端地址的行为。客户端负责启动所有
迁移。 服务器不会向客户端地址发送非
探测包（请参阅{{probing}}），直到服务器收到
来自该地址的非探测包。 如果客户端从未知服务器
地址收到包，则客户端**必须**丢弃这些包。


## 探测一个新的链路(Probing a New Path) {#probing}
某一端可以为新的本地地址的对端可达性作探测，
采取之前提到{{migrate-validate}}的链路验证的方式
将连接迁移到一个新的本地地址.
链路验证失败表明新的链路对该连接不适用。
除非没有其他可以替代的有效链路，
链路验证失败并不会导致连接关闭。
每次从新的地址探测时，
端上都会使用一个新的连接id，
进一步的讨论可以参考{{migration-linkability}} 。
使用新地址的一端必须确保对端可以提供
至少一个新的连接id，
这种保证是通过在探测的时候添加一个
NEW_CONNECTION_ID 帧来实现的。

从对端接收到一个PATH_CHALLENGE帧的时候
表明该对端正在探测一条链路的可达性，
本端会按照{{migrate-validate}}回复一个PATH_RESPONSE帧。

PATH_CHALLENGE, PATH_RESPONSE,
NEW_CONNECTION_ID, 和 PADDING 帧都是”探测帧“，
其他的帧都是“非探测帧”。
只包括探测帧的包是一个“探测包”，
包括其他帧的包都是“非探测包”。

## 初始化连接迁移(Initiating Connection Migration) {#initiating-migration}

在从新地址发送非探测包的时候，
就表明该端迁移连接到了新地址。
在连接建立的时候，每端都会验证对端的地址。
因此，当一个正在迁移的某端可以向对端发送消息时表明
对端在当前的地址已经准备好接受消息了。
即在迁移到新的地址的时候，
该端不用提前验证对端的地址。

当迁移的时候，
新的链路或许不能支持端上当前的发送速率。
因此，该端需要重置拥塞控制器，详见{{migration-cc}}}

新的链路或许没有同样的ECN能力，
因此，该端需要确认下ECN能力，见{{ecn}}.

在新的链路上发送的数据收到ack的时候表明对端是可达的。
注意由于ack可以从任何链路上收到，
在新链路上的返回可达性尚未建立。
端上需要在新的链路上并发地开始
链路验证{{migrate-validate}}才可以确定新链路上的返回可达性。


## 对连接迁移的响应(Responding to Connection Migration) {#migration-response}

从新的对端地址收到一个非探测包的的时候
表明该端已经迁移到了新的地址。

作为对该包的回应，
端上必须开始将后续的包发往新的对端地址，
同时为了验证对端都未验证地址的所有权，
端上必须开始链路验证{{migrate-validate}}。

端上可以向未验证的对端地址发送内容，
但是必须避免潜在的攻击，
见 {{address-spoofing}} 和{{on-path-spoofing}}.
如果对端的地址近期出现过，
端上也可以跳过验证对端地址。

端上只会对标号最高的非探测包作为回应，
改变发包的地址。这样保证了在收到重排序的包的情况下，
端上不会为老的对端地址继续发包。

端上在改变了地址为发送非探测包的地址后，
就可以放弃其他地址的链路验证。

在验证了新的客户端地址之后，服务端可以
向客户端发送新的地址验证token。({{address-validation}})

### 对端地址欺骗(Peer Address Spoofing) {#address-spoofing}
对端有可能欺瞒原地址，
导致端上向一个错误的host发送大量的数据。
如果端上为欺骗的对端发送了大量的数据，
连接迁移就会被用来放大攻击者
生成的数据的流量流向受害者。

如{{migration-response}}所描述，
端上需要验证对端的地址，来确保对端对新地址的所有权。
端上必须限制发送数据的速率，
直到对端的地址被认为是有效的。
每个预估的RTT时间内，
端上不能发送超过最小拥塞窗口的数据
(kMinimumWindow, {{QUIC-RECOVERY}}).如果没有这个限制，
就会有对非目标受害者发起拒绝服务攻击的风险。
需要注意的是，端上不会有对改地址的任何RTT时间衡量，
估算的时间为初始的默认时间（见{{QUIC-RECOVERY}})。

如果端上跳过了对端地址的验证，
详见{{migration-response}},就不会限制发送速率。


### 链路上的地址欺骗(On-Path Address Spoofing) {#on-path-spoofing}

链路上的攻击者可以在真实的包到达之前通过复制
和发送虚假地址包的方式引起伪造的连接迁移。
带有虚假地址的包将会被认为是来自一个迁移中的连接，
原始的包就会被认为是重复的然后被丢弃。
在虚假的连接迁移之后，源地址的验证会失败，
因为来自源地址的内容中不会包括必须的加密密钥，
来读取或者响应发送给它的PATH_CHALLENGE帧，即使它想要。

为了保护连接的免于虚假迁移导致的失败，
在对端地址验证失败的时候，端上必须回退到上次
有效的对端地址。

如果端上没有上次有效的对端地址，
那么就必须通过丢弃所有连接状态
的方式默默地关闭掉连接。
这样在连接上的新包都会被统一处理。
例如，端上可以为后续进来的包都回复一个无状态的重置。

注意来自合法对端地址的带有较高标号的
包会触发新的连接迁移。
这样虚假迁移的地址验证就会被丢弃掉。


### 链路外的包导向(Off-Path Packet Forwarding) {#off-path-forward}

一个链路外可以看到包的攻击者
可以将真实包的复制包导向某一端。
如果复制的包比真实包之前到，会表现为NAT重绑定。
任何真实的包都会被认为重复而丢弃。
如果攻击者能够继续导包的话，
可以造成连接迁移到一个经由攻击者的链路上。
这样就会把攻击者置于链路中间，
就可以观测或者丢弃后续的包了。

并不像{{on-path-spoofing}}描述的攻击，
这样攻击者可以保证新的链路是可以被有效验证的。

这种类型的攻击在于攻击者使用了一个跟双端直接连接
近乎相同速度的链路。如果很少的包正在发送，
或者攻击的同时伴随丢包情况，这种攻击就很有效。

在原始的链路接收到一个增加了收到包标号的最大值的
非探测包的时候，端上就会迁移回原来的链路。原始链路
上引出来的包增加了攻击失败的概率。因此，攻击性的迁
移在于触发包的交换。

作为明显的连接迁移的回应，端上必须使用PATH_CHANLLENGE
帧验证之前有效的链路。如果链路是不可达的，
尝试验证就会超时而失败；
如果链路是可达的，但是不再被用，验证会成功
但是，只有探测包会在链路上发送。

在活跃的链路上接收到PATH_CHALLENGE报文的端上应该发送
非探测包作为回应。
如果非探测包在任一攻击者复制的包之前到达，
连接就会被迁移回原来的链路。任何后续的迁移都会重
新开始这整个流程。

这种防御并不是完美的，
但这并不被认为是一个严肃的问题。如
果攻击者的链路在多次尝试
使用原始链路的情况下仍然比原始链
路可靠迅速，那就不可能区分是攻击者还是路由上的改进。

端上也可以使用启发式的方式改进对这种攻击类型的探测。
例如，
如果刚刚从老的链路接收到包NAT重新绑定
是不大可能发生的，在
IPV6的链路上类似的绑定也是很少的。相反，connectionID的
改变更可能表明有意识的迁移而不是攻击。

## 丢失检测和拥塞控制（Loss Detection and Congestion Control） {#migration-cc}

新链路的容量有可能和老链路的不同。
在旧链路发送的包不应该对
新链路的拥塞控制或RTT预测起作用。

在确认对端新地址的所有权的时候，
端上必须立刻重置新链路的拥
塞控制器和RTT估算器，

端上**禁止**将发送速率设置为之前链路使用的设置，
除非有充分
的理由之前的速率对新链路同样适用。
例如，客户端端口的改变很有
可能表明中间件的重新绑定而不是链路的更新。
这种决定很有可能是
基于推断的，也是不完善的；
如果新的链路容量急剧降低，毫无疑问
是拥塞控制器对拥塞信号的反应，
适当降低了发送速率。

在端上发送数据时接收方有可能有明显的重排序，
同时在连接迁移的
时候会在多个往返地址上发送探测包，
因此会导致两个探测出来的链
路有不同的往返时间。
多个链路上的包接受者仍旧会为所有接收到的
包发送ACK帧。

尽管在连接迁移的时候多个链路有可能被使用，
单个拥塞控制上下文
和单个丢失重传上下文就够用了（详见{{QUIC-RECOVERY}}），例
如，端上在确认旧链路已经不被使用
的时候才会将相关信息传递给新
的拥塞控制上下文，（参照{{off-path-forward}}）

发送者可以为探测包做例外的处理，
使得这些包的丢失检测是单独的
不会过度导致拥塞控制器降低发送速率。
端上可以单独设置一个
PATH_CHALLENGE帧发出的计时器，
但对应的PATH_RESPONSE包收到的
时候取消掉。
如果在PATH_RESPONSE包接收到之前定时器被触发，
端上可以重新发个PATH_CHALLENGE帧,
同时为定时器设置一个更长的
时间.

## 连接迁移的私密性实现(Privacy Implications of Connection Migration) {#migration-linkability}

在不同的网路链路之间使用稳定的连接id可以
使被动的观察者在关联起
这些链路之间的活动。
端上在不同的网路之间移动的时候或许不想让除
了对端以外其他方关联到它们的活动，
因此从不同的本地地址发送的时
候会使用不同的连接Id，
详见 {{migration-cc}}.端上必须保证他们提
供的连接id不会被其他方关联到，才能保证私密性生效。

这样在同一连接不同网络的关联活动去掉了连接id的使用。
头部保护确
保在关联活动时包下标不会被用于关联活动，
但是不能保证包的其他属
性例如计时和大小不会被用于关联活动。

客户端**可以**基于具体实现随时移动到新的连接id。
例如，在一段时间网络不活跃之后，
客户端发送数据的时候已经发生了NAT重绑定。

在一段时间的不活跃之后，
客户端或许想要在发送流量的时候通过启用
新的连接id和udp端口的方式来降低可达性。
在发送包的时候改变udp端
口可以该包表现为连接迁移。
这样确保了在客户端没有经历NAT重绑定
或者真实的连接迁移的时候，
支持连接迁移的机制也是可以被练习的。
更新端口号会造成对端重置它的拥塞状态
（详见 {{migration-cc}}），
因此端口**应该**不被频繁的更新。

如果对端在连接迁移之后使用同样的目的连接id，
使用长度大于0的连接
ID的端上就会将这些活动关联起来。
端上在接收到一个未使用过的目
的连接id的包的时候，
应该将连接id更新为没有被其他网络链路使用过的
连接id。
这里的目的是确保不同链路上的包不会被关联起来。
为了实现
这种隐私性的要求，
开始连接迁移并且使用大于0长度连接ID的端上**应
该**在连接迁移之前为对端提供新的连接ID。

注意：如果在观察到对端的连接ID更新的时候，
双端都更新连接id作为回
应，这样就会触发一轮无限的更新循环。


## 服务端首选地址（Server's Preferred Address） {#preferred-address}

Quic协议允许服务端接受一个id地址上的连接，
然后尝试在握手之后将连接转移到另一
个更倾向的地址。
这一点在客户端初始连接到了一个被多个
服务端共享但更倾向于使用
单播地址来确保连接稳定性的时候尤其有用。
这部分内容描述将连接迁移到一个首选
服务端地址的协议。

将连接迁移到一个新的服务端地址的时候，
对于将来的工作留下了半连接的状态。如果
客户端接收到了一个不被传输参数
preferred_address标识的新的服务端地址，
那么客户端**应该**把这些包丢弃掉。

### 商议一个首选地址（ Communicating A Preferred Address）

服务端通过在TLS握手中添加一个
preferred_address传输参数来传达一个首选的地址。

服务端**可以**为每个协议簇（ipv4和ipv6）
设定一个首选的地址，让客户端来自己选
择最适合它们网络附件的一个。

一旦握手完成，
客户端**应该**在服务端首选地址里选择一个，
然后利用在preferred_address的传输参数
里面指定的连接id初始化链路验证。详见{{migrate-validate}}.

如果链路验证成功了，
客户端**应该**立即开始利用新的连接id发送所有的后续包到
新的服务端地址，终止掉旧的服务器地址。
如果链路验证失败，客户端**必须**继续
向原有的服务端地址发送后续的包。

### 对连接迁移的响应(Responding to Connection Migration)

服务端可能在它接受链接后的任何时候接收到
指向它首选的 IP 地址的包。
如果这个包包含了一个 PATH_CHALLENGE 帧，
服务端发送一个和对端一样的 PATH_RESPONSE 帧{{migrate-validate}}。
服务端**必须**从其原始地址发送其它非探测帧，
直到它在自己首选地址从客户端收到了非探测包，
且服务端已经验证了新的路径。

服务端**必须**从首选地址探测到客户端的路径。
这有助于防卫来自攻击者的伪造的连接迁移请求。

一旦服务端完成了路径探测并且已经在首选地址
收到了一个带着新的最大包数非探测包，
服务端开始仅从首选地址发送非探测包给客户端。
它**应该**丢弃这个连接上接收到的旧 IP 地址的包，
但是**可能**继续处理延迟的包。


### 首选地址与链接迁移之间的交互(Interaction of Client Migration and Preferred Address)

客户端可能需要在它迁移到服务端的首选地址
之前执行连接迁移。
在这种场景下，客户端**应该**并行的执行从
客户端的新地址到原始地址和首选地址之间的路径验证。

如果到服务端首选地址的路径验证成功，
客户端**必须**放弃到原始地址的验证
并且迁移去使用服务端的首选地址。
如果到服务端首选地址的路径验证失败
但是到原始地址的路径验证成功，
客户端**可能**迁移到新的地址
并且继续发送到服务端的原始地址。

如果到服务端首选地址的连接并
不是来自相同的客户端地址，
服务端**必须**防御在{{address-spoofing}} 和
{{on-path-spoofing}}中描述的可能的潜在攻击者。
除了有意的迁移之外，这也可能因为客户端使用了绑定
在服务端首选地址上的不同的NAT连接网络出现。

服务端**应该**在接收到来自不同地址的探测包的时候
初始化到客户端新地址的路径验证。
服务端**禁止**在路径验证完成前发送
超过最小拥塞窗口的值的非探测包到新的地址。

迁移去新地址的客户端**应该**
使用与服务端相同地址族的首选地址。


## IPv6流标签与迁移的使用(Use of IPv6 Flow-Label and Migration) {#ipv6-flow-label}

使用 IPv6 发送数据的终端**应该**
应用符合{{!RFC6437}}的 IPv6 流标签，
除非本地的 API 不允许设置 IPv6 流标签。

IPv6 流标签**应该**是一个源与目标地址、
源于目标UDP端口以及目标CID的伪随机函数。
流标签的生成**必须**设计为最小化
使用与之前使用过的流标签的可连接性，
因为这将允许在多个路径上进行关联行为。
(详见{{migration-linkability}})

一种可能的实现是将流标签作为源和目标地址、
源和目标UDP端口，
目标CID以及本地密钥的加密哈希函数来计算。


# 连接终止（Connection Termination） {#termination}

在没有操作的时候连接是默认打开的，除非闲置了一段时间，
这个时间是预先定义的。一个已经建立好的
QUIC连接遇到一下情况会终止。

* 闲置超时（{{idle-timeout}}）
* 立即关闭（{{immediate-close}}）
* 无状态重置（{{stateless-reset}}）


## 关闭中和释放中状态（Closing and Draining Connection States） {#draining}

关闭中和释放中状态是为了确保连接在关闭的时候
是干净的，并确保延迟或乱序的包被正确丢弃。
这些状态**应该**保持至少三倍于在{{QUIC-RECOVERY}}
中定义的探测超时（PTO）间隔。

当一个终端开始立即关闭流程（{{immediate-close}}）时进入
关闭中阶段。在关闭中，除非是包含CONNECTION_CLOSE帧的包否则
终端**必须不**发送任何包（查看{{immediate-close}}以获得详细信息）。
终端只保留用于生成包含CONNECTION_CLOSE帧的包的信息，
并将数据包标记为属于该链接。
终端选择的连接ID和QUIC版本就足够
来标记包属于哪个关闭中的连接；终端
可以丢弃其他所有的连接状态。终端**可能**为
读取和处理CONNECTION_CLOSE帧而保留
传入包的包保护密钥。

当一个终端收到它的对端进入关闭中或释放中状态的信号时立即
计入释放中状态。同关闭中状态一致，处于释放中状态的终端
**必须不**发送任何包。连接进入释放中状态时就没有必要再
保存包保护密钥。

端点在收到CONNECTION_CLOSE帧或无状态重置时**可能**回从
关闭中状态转换到释放中状态，这两种情况都表明对端也在
关闭中或释放中。当关闭中周期结束的时候释放中周期也必须结束。
也就是说，终端可以使用相同的结束时间，
但是停止重传关闭中包。

*(这一点没怎么看懂，加了点意译)*
在关闭中周期或释放中周期结束前处理连接的状态 *(猜测可能是想说在超时之前把连接状态给改了)*
*(所以在closing和draining状态之后还能到其他状态？)*
会导致延迟或乱序的包不能被正确处理。有某种能
确保连接上延迟到达的包不创建QUIC状态的终端 *(结合下面感觉是说一个延迟的包到达，但是这个时候此连接)*
*(在此终端上已经不是closing或draining状态而是导致这个延迟的包把此链接的状态再次改变了)*
**可能**使用较短的释放周期和关闭周期来更快的回复资源，例如
可以关闭UDP套接字的终端。保留用于接受新连接的 *(把UDP socket关了就不回有问题了)*
开放套接字的服务器**不可以**提前退出关闭或耗尽周期。*(一个UDP套接字有多个连接一个关了socket不关)*
*(所以这个socket还能收到已经关闭的连接的延迟到达的包，导致已经被关闭的连接又进入新的状态)*
*(如果是这样理解没错的话那就是终端记录每个socket已关闭的连接收到延迟包以后直接丢弃也行)*

一旦关闭中或释放中周期结束了，终端**应该**丢弃此
连接的所有状态。这样这个连接上新的包就能被正常处理。
比如，终端**可能**发送无状态重置
来相应之后传入的包。

当发送无状态重置（{{stateless-reset}}）时
释放中和关闭中状态不适用。

处于关闭中或释放中的终端不需要处理 *(密钥？健？)* 更新。
Key更新可能会阻止终端从关闭中状态转向释放中状态，
但实际上它应该没有任何影响。

终端在关闭中周期时可能接收到来自新地址的
连接迁移（{{migration}}）。处于关闭状态的端点
**必须**严格限制发送到此新地址的包的数量，
直到该地址经过验证（参见{{migrate-validate}}）。处于
关闭中状态的终端**可以**选择丢弃从新地址
接收来的包。


## 闲置超时（Idle Timeout） {#idle-timeout}

如果启用了空闲超时，则当连接持续空闲时间超过预公布的空闲超时
（参见{{transport-parameter-definitions}}）和三倍
当前探测超时（PTO）的最大值时会被静默关闭，并且连接的
所有状态都会被抛弃。

每个终端都会给对端公布自己的闲置超时。终端
在收到并成功处理其对端发送的包后重置自己维护的
任何计时器。当收到一个包且没有发送其他ACK诱发包时，
发送任何不包含ACK或PADDING
（一个ACK诱发包，参见{{QUIC-RECOVERY}}）
帧的包也会重置计时器。发送包的时候重置计时器
能确保在启动新活动时连接不会过早的超时。

闲置超时的值可以是不对等的。终端公布的值
仅仅时用来确定此终端上的连接是否
处于活动状态。终端在对端闲置超时周期快要结束的时候发送
的包可能会因为对端在收到包之前就进入释放状态而被丢弃。
如果对端可能在一个探测超时（PTO，参见{{QUIC-RECOVERY}}）
时间内超时，建议在发送任何不能安全重发的数据之前
测试连接的活动状态。


## 立即关闭（Immediate Close）

终端可以发送CONNECTIN_CLOSE帧（{{frame-connection-close}}）来
马上立即终止连接。CONNECTION_CLOSE帧会让
所有的流马上被关闭；可以假定开放流都被
隐式重置。

终端在发送CONNECTION_CLOSE帧之后马上进入关闭中状态。
在关闭中周期中，发送CONNECTION_CLOSE的终端
**应该**在答复任何接收到的包的同时发送额外的包含
CONNECTION_CLOSE帧的包。为了最小化
终端在关闭中维护的状态，终端**可能**重复发送完全一样的包。
但是终端**应该**限制包含CONNECTION_CLOSE帧的额外包的数量。
例如，端点可以逐渐增加两次额外包之间
收到包的数量或者两个额外包
之间的时间间隔。

注意：

: 允许重传关闭包和本文档中为每个包创建
  新包号码的建议相矛盾。
  发送新的包号码主要有利于丢失恢复
  和用赛控制，这与关闭的连接不相关。
  重传最终包所需要的状态很较少。*（没怎么看懂）*

从未验证的地址发来的包可能是用来创建
放大攻击的（参见{{address-validation}}）。为了避免此攻击，终端**必须**选择
对发送到经验证地址的CONNECTION_CLOSE帧做限制，
或者不答复直接丢弃答复包的大小比接收到的数据大小
大三倍的包。

终端在收到CONNECTION_CLOSE帧以后进入释放中状态。
收到CONNECTION_CLOSE的终端**可能**再进入
释放中状态之前发送一个包含CONNECTION_CLOSE的单个包，如果需要
可以使用CONNECTION_CLOSE帧和NO_ERROR码。终端**必须不**
发送更多的包，因为这会导致在一方结束周期结束之前双方
不停的交换CONNECTION_CLOSE帧。

在应用协议安排关闭连接之后可以使用立即关闭。
这可能是在应用协议正常关闭之后。
两端的应用协议进行了充分的协商并、
都同意关闭连接，之后
应用程序请求关闭连接。应用协议
可以使用带有适当错误码的CONNECTION_CLOSE帧
来指示关闭。

连接成功建立后，终端**必须**在1-RTT包中发送
CONNECTION_CLOSE帧。在连接简历之前
对端可能没有1-RTT密钥，因此终端**应该**在
握手（Handshake）数据包中发送CONNECTION_CLOSE帧。如果终端没有握手密钥，或者
不确定对等设备是否有握手密钥，它**可以**在初始化（Initial）包
中发送CONNECTION_CLOSE帧。如果发送多个数据包，可以
合并（参见{{packet-coalesce}}）以便重传。

## 无状态重置(Stateless Reset) {#stateless-reset}

无状态重置是提供给无法访问连接状态的终端的最后选择。
崩溃或中断可能导致对端继续向无法继续正常连接的终端发送数据。
无状态重置不适用于发出错误条件的信号。
如果终端有足够的状态，则希望通信致命连接错误的终端**必须**使用CONNECTION_CLOSE帧来通信。


为了支持这个过程，终端发送一个令牌。
令牌在任一对端发送的NEW_CONNECTION_ID帧中携带，服务器可以在握手期间
指定stateless_reset_token传输参数(客户机不能，因为它们的传输参数没有机密性保护)。
此值受加密保护，因此只有客户机和服务器知道此值。
当令牌的关联连接ID通过RETIRE_CONNECTION_ID帧
({{frame-retire-connection-id}})停用时，令牌将失效。


接收到无法处理的数据包的终端发送数据包的布局如下:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|0|1|               不可预知的位数  (182..)                ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                                                               +
|                                                               |
+       无状态重置令牌(Stateless Reset Token) (128)                 +
|                                                               |
+                                                               +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #fig-stateless-reset title="无状态重置令牌(Stateless Reset Packet)"}


这种设计确保无状态重置包尽可能与具有短报头的常规包没有区别。


无状态重置使用整个UDP数据报，从数据包头的前两位开始。
第一个字节的剩余部分及其后的任意数量的字节被设置为不可预测的值。
数据报的最后16个字节包含一个无状态重置令牌。


无状态重置将被接收者解释为具有短报头的包。
要使数据包显示为有效的，不可预测位字段至少需要包含182位数据
(或23个字节，减去两个固定位)。
这是为了允许目标连接ID具有最大允许长度、最小包号和有效负载。
无状态重置令牌对应于包保护AEAD的最小扩展。
如果终端可以协商使用更大的最小AEAD扩展的包保护方案，则可能需要更多不可预测字节。


终端**不应**发送比其接收的包大得多的无状态重置。
终端**必须**丢弃太小而不能作为有效的QUIC包的包。
使用{{QUIC-TLS}}中定义的一组AEAD函数，小于21字节的包永远无效。


终端**可以**发送无状态重置来响应具有长报头的包。
如果对端还不能使用无状态重置令牌，则此方法将无效。
在这个QUIC版本中，只有在建立连接时才使用长报头的数据包。
由于无状态重置令牌在连接建立完成或接近完成之前不可用，因此忽略具有长报头的未知包可能更有效。


终端无法从具有短报头的包中确定源连接ID，因此它无法在无状态重置包中设置目标连接ID。
因此目标连接ID将与前面包中使用的值不同。
随机目标连接ID使连接ID看起来是移动到使用NEW_CONNECTION_ID帧
({{frame-new-connection-id}})提供的新连接ID的结果。


使用随机连接ID会导致两个问题:

* 数据包可能无法到达对端。如果目标连接ID对于路由到对端非常重要，
  则此包可能被错误路由。这还可能触发另一个无状态重置，参见{{reset-looping}}。
  没有正确路由的无状态重置是无效的错误检测和恢复机制。
  在这种情况下，端点将需要依赖于其他方法(例如计时器)来检测连接是否失败。

* 随机生成的连接ID可用于对端以外的实体，以将其标识为潜在的无状态重置。
  偶尔使用不同连接id的终端可能会对此带来一些不确定性。


最后，数据包的最后16个字节被设置为无状态重置令牌的值。


这种无状态重置设计是特定于QUIC版本1的。
支持多个QUIC版本的终端需要生成一个无状态重置，
该重置将被终端可能支持的任何版本(或在丢失状态之前可能已经支持的版本)的对端接受。
新版本的QUIC的设计者需要意识到这一点，或者重用这个设计，
或者使用包的一部分而不是最后16个字节来携带数据。

### 检测无状态重置(Detecting a Stateless Reset)

当具有短报头的传入包不能与连接关联、不能被解密或被标记为重复包时，
终端检测潜在的无状态重置。
然后，端点将数据包的最后16个字节与它的对端提供的无状态重置令牌
(在NEW_CONNECTION_ID帧中或服务器的传输参数中)进行比较。
如果这些值相同，终端**必须**进入耗尽期，并且在此连接上不再发送任何数据包。
如果比较失败，可以丢弃这些数据包。


### 计算无状态重置令牌(Calculating a Stateless Reset Token) {#reset-token}

无状态重置令牌**一定**很难猜测。
为了创建无状态重置令牌，终端可以为它创建的每个连接随机生成{{!RFC4086}}一个密码。
然而，当集群中有多个实例或终端的存储问题可能会丢失状态时，就会出现协调问题。
无状态重置专门用于处理状态丢失的情况，所以这种方法不是最优的。

通过使用抗预映像函数的第二次迭代生成证明，单个静态密钥可用于到同一终端的所有连接，
该函数将静态键和终端选择的连接ID作为输入(请参见{{connection-id}})。
终端可以使用HMAC {{?RFC2104}}(例如，HMAC(static_key, connection_id))
或HKDF {{?RFC5869}}(例如，使用静态密钥作为输入密钥，连接ID作为salt)。
此函数的输出被截断为16字节，以生成该连接的无状态重置令牌。

丢失状态的终端可以使用相同的方法生成有效的无状态重置令牌。连接ID来自终端接收的包。

这种设计依赖于对端总是在其包中发送连接ID，以便终端可以使用包中的连接ID重置连接。
使用此设计的终端**必须**对所有连接使用相同的连接ID长度，
或者对连接ID的长度进行编码，以便可以在没有状态的情况下恢复连接ID。
此外，它不能提供零长度的连接ID。


显示无状态重置令牌允许任何实体终止连接，因此值只能使用一次。
这种选择无状态重置令牌的方法意味着连接ID和静态密钥的组合不能在另一个连接发生。
如果共享静态密钥的实例使用相同的连接ID，
或者如果攻击者可以导致数据包路由到只有相同静态密钥(请参阅{{reset-oracle}})的实例，
则可能发生拒绝服务攻击。
通过显示无状态重置令牌重置的连接的连接ID不能用于共享静态密钥的节点上的新连接。

请注意，无状态重置包没有任何加密保护。


###循环(Looping) {#reset-looping}

无状态重置包的设计使得在不知道无状态重置令牌的情况下，它与有效数据包无法区分。例如，
如果一台服务器向另一台服务器发送无状态重置包，它可能会收到另一台无状态重置包作为响应
，这可能导致无限的交换。

终端必须确保它发送的每个无状态重置包都小于触发它的数据包，除非它保持足以防止循环的状
态。在发生循环的情况下，数据包会因为太小而无法触发响应。

终端可以记住已发送的无状态重置数据包的数量，并在达到限制后停止生成新的无状态重置数据
包。对不同的远程地址使用单独的限制将确保在其他对端或连接耗尽限制时可以使用无状态重置
数据包来关闭连接。

将无状态重置包的大小减小到建议的最小大小39字节以下，这意味着数据包可能会向观察者显示
它是无状态重置包。相反，拒绝响应小数据包而发送无状态重置包可能导致无状态重置包无法在
仅发送非常小的数据包的情况下检测中断连接的情况；此类故障可能只能通过其他方式(如计时
器)来检测。

如果数据包不能通过将其填充到至少40字节来处理，则终端可以增加数据包触发无状态重置的可
能性。


#错误处理(Error Handling) {#error-handling}

检测到错误的终端**应该**将该错误的存在通知其对端。传输级和应用级错误都会影响整个连接
(参见 {{connection-errors}})，而只有应用级错误才能被隔离到单个流中(参见 {{stream-errors}})。

发出错误信号的帧中**应该**包含最合适的错误代码({{error-codes}})。在描述标识错误状况
处，还标识了所使用的错误代码。

无状态重置({{stateless-reset}})不适用于可以用CONNECTION_CLOSE或RESET_STREAM帧发出
信号的任何错误。具有在连接上发送帧所需状态的终端**禁止**使用无状态重置。


##连接错误(Connection Errors) {#connection-errors}

导致连接不可用的错误(如明显违反协议语义或影响整个连接的状态损坏)**必须**使用
CONNECTION_CLOSE帧发出信号({{frame-connection-close}})。即使错误只影响单个流，终端
也**可能**以这种方式关闭连接。

应用协议可以使用CONNECTION_CLOSE帧的特定于应用的变体发送特定于应用的协议错误信号。特
定于传输的错误，包括本文档中描述的所有错误，都带有CONNECTION_CLOSE帧的特定于QUIC的
变体。

可以在丢失的数据包中发送CONNECTION_CLOSE帧。如果终端在终止的连接上接收到更多的数据包
，则**应该**准备重新传输包含CONNECTION_CLOSE帧的数据包。限制重新传输的次数和发送此最
终数据包的时间限制了终止连接所花费的努力。

选择不重新传输包含CONNECTION_CLOSE帧的数据包的终端有丢失第一个此类数据包的风险。对于
继续接收终止连接数据的终端来说，唯一可用的机制是使用无状态重置过程({{stateless-reset}})。

接收无效的CONNECTION_CLOSE帧的终端不能向其对端发出错误存在的信号。


##流错误(Stream Errors) {#stream-errors}

如果应用级错误影响单个流，换句话说在排除该连接的情况下处在可恢复状态，则端点可以发送
包含适当错误代码的RESET_STREAM帧({{frame-reset-stream}})，以终止受影响的流。

RESET_STREAM**必须**由使用QUIC的协议发起，可以是直接发起，也可以是通过从对端接收
STOP_SENDING帧来执行。RESET_STREAM带有应用错误代码。在不知道应用协议的情况下重置流
可能会导致协议进入不可恢复状态。应用协议可能需要可靠地传输某些流，以确保终端之间的状
态一致。


#数据包和帧(Packets and Frames) {#packets-frames}

QUIC终端通过交换数据包进行通信。数据包具有机密性和完整性保护(参见 {{packet-protected}})
，并在UDP数据报中传输(参见 {{packet-coalesce}})。

此版本的QUIC在连接建立过程中使用长数据包报头(参见 {{long-header}})。具有长报头的数
据包是初始数据包({{packet-initial}})、0-RTT数据包({{packet-0rtt}})、握手数据包
({{packet-handshake}})和重试数据包({{packet-retry}})。版本协商使用带有长报头的独立
于版本的数据包(参见 {{packet-version}})。

具有短报头({{short-header}})的数据包是为了最小的开销而设计的，在建立连接和1-RTT密钥
可用后使用。


##受保护的数据包(Protected Packets) {#packet-protected}

除版本协商和重试数据包外，所有QUIC数据包都使用带有附加数据 (AEAD) {{!RFC5116}}的身份
验证加密，以提供机密性和完整性保护。数据包保护的详细信息可在{{QUIC-TLS}}中找到，本节
包括此过程的概述。

初始数据包使用静态派生的密钥进行保护。此数据包保护不是有效的机密性保护。初始保护仅存
在于确保数据包的发送方位于网络路径上。从客户端接收初始数据包的任何实体都可以恢复删除
数据包保护或生成能通过验证的数据包所需的密钥。

所有其他数据包都使用从加密握手数据包派生的密钥进行保护。来自长报头的数据包类型或来自
短报头的密钥阶段用于标识所使用的加密级别(因此也就是密钥)。使用0-RTT和1-RTT密钥保护的
数据包应该具有机密性和数据来源身份验证；加密握手数据包确保只有通信终端接收相应的密钥。

Packet Number字段包含一个Packet Number，它用来在应用数据包保护后应用额外机密性保护
(详情参见 {{QUIC-TLS}})。基础Packet Number随着每个数据包在给定Packet Number空间中
的发送而增加(详情参见 {{packet-numbers}}) 。


## 合并包（Coalescing Packets） {#packet-coalesce}

初始 ({{packet-initial}})、0-RTT ({{packet-0rtt}})

和握手({数据包-握手})包包含一个长度字段，
用于确定包的结尾。包的长度包括包编号和
有效负载字段，这两个字段都经过加密保护
且初始长度未知。当删除报头保护后，
就可以知道“有效负载”字段的长度。

通过使用长度字段，发送方可以将多个QUIC包
合并为一个UDP数据报。这可以减少完成
加密握手和开始发送数据所需的UDP数据报数。
接收方**必须**能够处理经过合并处理的包。

按照加密级别增加(初始、0-RTT、握手、1-RTT)的
顺序合并数据包，能使接收方更有
可能处理在单次传输中所有的包。
短报头的包的头部不包含长度字段，
因此它只能是UDP数据报中包含的最后一个包。

发送方**禁止**将不同连接的QUIC包合并到
单个UDP数据报中。接收方**应该**忽略
任何具有与数据报中第一个包不同的目的
连接ID的后续数据包。

每个合并入单个UDP数据报的QUIC包都是
独立和完整的。虽然包报头中某些字段的值
可能是冗余的，但合并不会省略任何字段。
合并QUIC包的接收方**必须**单独处理
每个QUIC包并分别确认它们，
就好像它们是从不同UDP数据报的负载
接收的一样。例如，如果包的
解密失败(因为密钥不可用或任何其他原因)，
接收方**可能**会丢弃
或缓冲数据包以供以后处理，
并且**必须**尝试处理剩余的包。

重试包({packet-retry})、
版本协商包。({Packet-Version})
和具有短报头的包({Short-Header})
不包含长度字段，因此同一UDP数据报
中这些包后面不能跟随其他包。


## 包编号（Packet Numbers） {#packet-numbers}

包的编号是介于0到2^62-1之间的整数。
这个数字用于确定用于包保护的加密随机数。
每个终端都为发送和接收维护一个独立的包编号。

包编号被限制在此范围内，是因为它们需要在ACK帧的
最大确认字段({frame-ack})中整体表示。
但是，在长或短报头中时，包编号会减少并
编码成1到4个字节(请参见{packet-encoding})。

版本协商({{packet-version}})和重试({{packet-retry}})包
不会包括包的编号。

在QUIC协议中包编号被分割为三个空间:


- 初始空间：所有初始包 ({{packet-initial}}) 的
包编号都在这个空间。
- 握手空间：所有握手包 ({{packet-handshake}})的
包编号都在这个空间。
- 应用数据空间: 所有0-RTT和1-RTT加密后的包
({{packet-protected}})的包编号都在这个空间。

正如{{QUIC-TLS}}}中所描述的那样，每
个类型的包都使用不同的保护秘钥。

从概念上讲，包编号空间是一个包
可以被处理和确认的上下文。
初始包只能和初始包保护密钥一起发送，
并且也只能在初始包中确认。
同样，握手包是经过握手加密级别
加密后发送的，只能在握手包中得到确认。

这强制了在不同包编号空间中发送的
数据之间的密码分离。
每个空间中的包编号从包编号0开始。
随后在同一包编号空间发送的包的
编号**必须**至少增加一。

在同一包编号空间中存在0-RTT和
1-RTT数据能使得两个包类型
之间的丢失恢复算法更加容易实现。

一个QUIC终端**禁止**在一个连接内
重用同一个包编号空间内的包号。
如果发送的包编号达到2^62-1，
发送方**必须**关闭连接，而无需
发送CONNECTION_CLOSE帧或任何其他包；
终端**可能**发送一个
无状态重置({{stateless-reset}})，
以响应接收到的其他包。

接收方**必须**丢弃一个新的未受保护的包，
除非接收方确定没有从相同的包编号空间中
处理另一个具有相同包编号的包。
由于{{QUIC-TLS}}第9.3节中所述的原因，
在删除包保护后**必须**进行重复抑制。
在{{?RFC4303}}的3.4.3节中可以找到一种
有效的重复抑制算法。

发送方的包编号编码和接收方的解码
在{{packet-encoding}}中进行说明。


## 帧和帧类型（Frames and Frame Types） {#frames}

如{{packet-frames}}中所示,
移除包保护后QUIC包的负载通常由帧序列组成。

版本协商、无状态重置和重试包不包含帧。


<!-- TODO: 本节仍需要编辑工作。不是所有包都包含帧 -->

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                             帧 1 (*)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                             帧 2 (*)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
                               ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                             帧 N (*)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #packet-frames title="QUIC Payload"}

QUIC负载**必须**包含至少一个帧，
并且**可能**包含多个不同类型的帧。

帧的数据**必须**能够塞入单个QUIC包，
并且**禁止**跨越QUIC包的边界。
每个帧都以“帧类型”开头，表示其类型，
后跟其他依赖于类型的字段:


~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       帧的类型    (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   依赖类型的字段   (*)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #frame-layout title="Generic Frame Layout"}

此规范中定义的帧类型在{{frame-types}}中列出。
STREAM帧中的帧类型用于携带其他特定于帧的标志。
对于所有其他帧，帧类型字段仅用于标识该帧。
{{frame-formats}}中对这些帧进行了更详细的说明。


| Type Value  | Frame Type Name      | Definition                     |
|:------------|:---------------------|:-------------------------------|
| 0x00        | PADDING              | {{frame-padding}}              |
| 0x01        | PING                 | {{frame-ping}}                 |
| 0x02 - 0x03 | ACK                  | {{frame-ack}}                  |
| 0x04        | RESET_STREAM         | {{frame-reset-stream}}         |
| 0x05        | STOP_SENDING         | {{frame-stop-sending}}         |
| 0x06        | CRYPTO               | {{frame-crypto}}               |
| 0x07        | NEW_TOKEN            | {{frame-new-token}}            |
| 0x08 - 0x0f | STREAM               | {{frame-stream}}               |
| 0x10        | MAX_DATA             | {{frame-max-data}}             |
| 0x11        | MAX_STREAM_DATA      | {{frame-max-stream-data}}      |
| 0x12 - 0x13 | MAX_STREAMS          | {{frame-max-streams}}          |
| 0x14        | DATA_BLOCKED         | {{frame-data-blocked}}         |
| 0x15        | STREAM_DATA_BLOCKED  | {{frame-stream-data-blocked}}  |
| 0x16 - 0x17 | STREAMS_BLOCKED      | {{frame-streams-blocked}}      |
| 0x18        | NEW_CONNECTION_ID    | {{frame-new-connection-id}}    |
| 0x19        | RETIRE_CONNECTION_ID | {{frame-retire-connection-id}} |
| 0x1a        | PATH_CHALLENGE       | {{frame-path-challenge}}       |
| 0x1b        | PATH_RESPONSE        | {{frame-path-response}}        |
| 0x1c - 0x1d | CONNECTION_CLOSE     | {{frame-connection-close}}     |
{: #frame-types title="Frame Types"}


在此版本的QUIC协议中，所有QUIC帧都是幂等的。
也就是说，一个有效的帧被接收多次时不会引起
不良的副作用或错误。

Frame Type字段使用可变长度整数编码(请参见{{integer-encoding}})，
但有一个例外，为了确保简单有效地实现帧解析，
帧类型**必须**使用尽可能短的编码。
虽然可以对本文档中定义的帧进行
2字节、4字节或8字节的编码，
但这些帧的“帧类型”字段是以单字节编码的。
例如，虽然0x4001是一个值为1的可变长度整数的
合法双字节编码，但是PING帧总是编码为单字节值0x01。
终端**可能**将接收到编码长度超过必要的帧类型视为
协议冲突类型的连接错误。


# 打包和可靠性（Packetization and Reliability） {#packetization}

发送方会将一个或多个帧捆绑在一起
放进一个QUIC包(请参见{{frames}})。

通过在QUIC包中绑定尽可能多的帧，发送方可以将每个包用的
带宽和计算成本降至最低。发送方**可能**在发送未达到
最大包装的包前等待一短段时间，
以捆绑多个帧，用以避免发送大量的小包。
协议的实现**可能**使用应用程序发送行为
或启发式的相关知识来确定是否等待
以及等待多长时间。这个等待期
是一个实现决策，实施时应谨慎保守，
因为任何延迟都可能会增加应用可感知的延迟。

流复用是通过将来自多个流的流帧交织到
一个或多个QUIC包中来实现的。
单个QUIC包可以包括来自一个或多个流的多个帧。

QUIC的优点之一是避免了跨多个流的行首阻塞。
当发生包丢失时，只有在这个包中有数据的
流被阻塞，以等待接收重传，
而其他流可以继续进行处理。
请注意，当来自多个流的数据被捆绑到单个QUIC包中时，
该包的丢失会使在这个包中有数据的所有流被阻塞。
建议实现协议时在不降低未填满数据包的传输效率的
情况下，发出的包中应捆绑尽可能少数量的流。


## 包处理和确认（Packet Processing and Acknowledgment） {#processing-and-ack}

在成功去掉包保护并且处理完包中包含的
所有帧之前**禁止**发送包的确认。
对于STREAM帧，这意味着数据已经排队准备
由应用程序协议接收，但这不要求确认数据已
被应用接受和处理。

一旦包被完全处理，接收方通过发送一个或多个包含
所接收包的编号的ACK帧来确认包已收到。

<!-- TODO: 关于处理部分我们需要介绍吗？
以及提出我们对协议的实现在处理
有效帧后出现错误的包的方式的期望？-->

### 发送ACK帧（Sending ACK Frame） {#sending-ack-frames}

终端**禁止**对收到的包含了除ACK和PADDING帧以外的帧的包，
发送一个以上只包含一个ACK帧的包。终端**禁止**对仅包含
ACK帧或PADDING帧的包，发送仅包含ACK帧的包作为响应，
即使在接收到的包之前存在包间隙也是如此。
这可以防止ACK的无限期反馈循环。
但是，当发送ACK帧以响应其他包时，
端点**必须**确认仅包含ACK或PADDING帧的包。

出于拥塞控制的目的{{QUIC-RECOVERY}}，
传输过程中会发送包含PADDING帧的包。
发送仅有PADDING帧的包可能会导致
发送方受到拥塞控制器的限制(如{{QUIC-RECOVERY}}中所述)，
而接收方不会对此发出确认。因此，发送方**应该**
确保包中除PADDING帧外还发送其他帧，
以从接收方获得确认。

接收方的延迟确认计时器的延迟**不应该**超过
当前RTT估计值或其在“max_ack_delay”传输参数
中指示的值。这可确保在接收到
需要进行确认的包时，
每个RTT中至少发送了一次响应。
发送方可以使用接收方的`max_ack_delay‘
值来确定基于计时器的重传超时。

在{{QUIC-RECOVERY}}中详细讨论了关于
生成确认频率的策略和含义。

为了将发送ACK范围(请参见{{ack-ranges}})缩小为
发送方尚未收到的范围，
接收方**应该**跟踪其对端已确认了哪些ACK帧。
当已确认包对ACK帧的大小没有贡献时，
接收方**应该**从将发出的ACK帧中排除这些包。

由于ACK帧不是作为对仅包含ACK帧包的响应而发送的，
因此发送了仅包含ACK帧的包的接收方，只有在发送方
将这些帧包含在包含非ACK帧的包中时才会收到对其的确认。
发送方**应该**尽可能将ACK帧与其他帧捆绑在一起。

为了限制接收方的状态或ACK帧的大小，
接收方**可能**限制它发送的ACK范围的数量。
即使接收方没有收到对端对其ACK帧的确认，
也可以这样做，这可能会导致
发送方不必要地重新传输某些数据。
标准QUIC{{QUIC-RECOVERY}}算法会在确认收到
足够新的包后声明旧包丢失。
因此，接收方**应该**重复确认
新接收的包而不是过去接收的包。

如果终端能够检测到它收到了
它没有发送的包的确认，终端**应该**将其
视为PROTOCOL_VIOLATION类型的连接错误。



### ACK帧和数据包保护（ACK Frames and Packet Protection）

ACK帧**必须**只在与被ACK的包有相同包编号空间的
包中传输(请参见{{packet-protected}})。
例如，使用1-RTT密钥进行保护的包**必须**通过同
使用了1-RTT密钥进行保护的包进行确认。

客户端发送使用0-RTT保护的包**必须**由
服务端在受1-RTT密钥保护的包中确认。
这可能意味着如果服务端加密握手消息
延迟或丢失，客户端将无法使用这些确认。
请注意，同样的限制也适用于服务端发送的
受1-RTT密钥保护的其他数据。

终端**应该**在较短的延迟内发送对包含CRYPTO帧的包的确认；
请参阅{{QUIC-RECOVERY}}的6.2.1节。


## 信息重传(Retransmission of Information)

确定丢失的QUIC数据包不会整包重传,
这同样适用于丢失数据包中包含的帧。
但是，帧中携带的信息根据需要可以在新帧中再次发送。

新帧和包用于携带确定已丢失的信息。
通常，当确认包含该信息的包丢失并且此包发送终止时，
会再次发送该信息。

* 根据{{QUIC-RECOVERY}}中的规则重新发送CRYPTO帧中发送的数据，
直到所有数据都被确认。
当相应加密级别的密钥已被丢弃时，
丢弃用于初始化和握手包中CRYPTO帧的数据。

* 在STREAM帧中发送的应用数据在新的STREAM帧中重传，
除非终端已为该流发送RESET_STREAM。
一旦终端发送了RESET_STREAM帧，
该流此后的STREAM帧都不需要了。

* 最新的确认集以ACK帧发送。
ACK帧**应该**包含所有未确认的确认，
如{{sending-ack-frames}}中所述。

* RESET_STREAM帧中有流传输取消请求时流仍将持续发送，
直到取消被确认或者所有流数据被对端确认
(流头部的"Reset Recvd"或"Data Recvd"状态信息到达即可)。
RESET_STREAM帧中的内容在重发时**禁止**更改。

* 类似地，取消流传输的请求
（同STOP_SENDING帧中编码的那样）
将持续发送，
直到流的接收部分进入“Data Recvd”或“Reset Recvd”状态。
参考{{solicited-state-transitions}}.

* 连接关闭信号（和包含CONNECTION_CLOSE帧的数据包）
在检测到数据包丢失时，不会再次发送,
而是参考{{termination}}响应。

* 当前连接最大数据以MAX_DATA帧发送。
如果包含最近发送的MAX_DATA帧的数据包被声明丢失，
或者终端决定更新限制，则在MAX_DATA帧中发送更新的值。
需要注意避免频繁发送此帧，
因为这样额度可能会频繁增大
并导致发送不必要的大量MAX_DATA帧。

* 当前最大流数据偏移量在MAX_STREAM_DATA帧中发送。
与MAX_DATA类似，
当包含流的最新MAX_STREAM_DATA帧的数据包丢失或更新限制时，
会发送更新的值，同时注意防止帧过于频繁地发送。
当流的接收部分进入“Size Known”状态时，
终端**应该**停止发送MAX_STREAM_DATA帧。

* 给定类型的流的额度在MAX_STREAMS帧中发送。
与MAX_DATA类似，当包含流类型帧的最新
MAX_STREAMS的数据包被声明丢失时或额度被更新时，
会发送更新的值，同时注意防止该帧过于频繁地发送。

* 阻塞的信号在DATA_BLOCKED，
STREAM_DATA_BLOCKED和STREAMS_BLOCKED帧中传送。
DATA_BLOCKED帧含有连接范围，
STREAM_DATA_BLOCKED帧含有流范围，
STREAMS_BLOCKED帧限定特定流类型。
如果包含范围的最新帧的数据包丢失，则会发送新帧，
但仅在终端在相应限制上被阻止时才会发送。
这些帧始终包含在被传输过程中会导致阻塞的限制值。

* 使用PATH_CHALLENGE帧的存活或
路径可用的检查结果会定期发送，
直到收到匹配的PATH_RESPONSE帧，
或者直到不再需要存活或路径可用的检查。
PATH_CHALLENGE帧每次发送时都包含不同的有效载荷。

* 使用PATH RESPONSE帧的路径验证响应仅发送一次。
如果需要另一个PATH_RESPONSE帧，
将发送新的PATH CHALLENGE帧。

* 新的连接ID在NEW_CONNECTION_ID帧中发送，
如果包含它们的数据包丢失则重新传输该包。
该帧的重传具有相同的序列号值。
同样，退出的连接ID在RETIRE_CONNECTION_ID帧中发送，
如果包含它们的数据包丢失则重新传输该包。

* PING和PADDING帧不包含任何信息，
因此丢失的PING或PADDING帧不需要修复。

除非应用程序指定的优先级另有说明，
否则终端**应该**优先通过发送新数据重新传输数据(参考
{{stream-prioritization}})。

即使鼓励发送方在每次发送数据包时
组装包含最新信息的帧，
也不禁止丢包重传发送旧帧的副本。
接收方**必须**接受包含过时帧的数据包，
例如包含最大数据量比当前旧数据包中的
最大数据量小的MAX_DATA帧。

在检测到丢包时，发送方**必须**采取适当的拥塞控制措施。
损失检测和拥塞控制的细节在{{QUIC-RECOVERY}}中描述。


## 显式拥塞通知(Explicit Congestion Notification) {#ecn}

QUIC终端可以使用显式拥塞通知
（ECN）{{!RFC3168}}来检测和响应网络拥塞。
ECN允许网络节点通过在分组的IP报头中
设置码点而不是丢弃它来指示网络中的拥塞。
如{{QUIC-RECOVERY}}中所述，
终端通过降低响应的发送速率来对拥塞作出反应。

要使用ECN，QUIC终端首先确定路径是否支持ECN标记，
并且对端能够访问IP标头中的ECN码点。
如果ECN标记的数据包被丢弃或ECN标记在路径上被重写，
则网络路径不支持ECN。
终端在连接建立期间和迁移到
新路径时会验证路径(参考{{migration}})。


### 显式拥塞计数（ECN Counts）

在接收到具有ECT或CE代码点的QUIC数据包时，
可以从封闭IP数据包访问ECN代码点的启用
ECN的终端会增加相应的ECT（0），
ECT（1）或CE计数，并在随后包含这些计数
ACK帧（见{{processing-and-ack}}和{{frame-ack}}）。
请注意，这需要能够从封闭的IP数据包中读取ECN代码点，
这在所有平台上都是不可能的。

由接收方检测为重复的数据包不会
影响接收方的本地ECN代码点计数。
有关上述动作的安全问题，请参阅({{security-ecn}})。

如果终端在IP数据包报头中收到
没有ECT或CE代码点的QUIC数据包，
它将根据{{processing-and-ack}}的响应，
使用ACK帧而不增加任何ECN计数。
如果终端未实现ECN支持或无法访问收到的ECN码点，
则不会增加ECN计数。

合并的数据包（参见{{packet-coalesce}}）
意味着几个数据包可以共享相同的IP报头。
在相关IP报头中接收的ECN码点的ECN计数器
对于每个QUIC包递增一次，
而不是每个封闭的IP包或UDP数据报。

每个数据包编号空间都保持单独的
确认状态和单独的ECN计数。
例如，如果初始化，0-RTT，
握手和1-RTT QUIC包每个各一个被合并，
则初始和握手包的编号空间的相应计数将递增1，
同时1-RTT包的编号空间计数加2。


### ECN校验(ECN Verification) {#ecn-verification}

每个终端通过将 IP 报头 ECN 代码点设置为从其到对端的路径的 ECN 能力传输(ECT)，
独立地验证并激活 ECN 的使用。
即使不在其传输的数据包上设置 ECN 代码点，终端也**应该**提供关于接收到的 ECN 标记的反馈(如果可访问的话)。

为了验证路径是否支持 ECN 以及对端是否可以提供 ECN 反馈，终端在所有传出数据包{{!RFC8311}}的 IP 报头中设置ECT(0)代码点。

如果 IP 报头中设置的 ECT 代码点集未被网络设备损坏，
则接收到的数据包包含对端设备发送的代码点或经历拥塞的网络设备设置的拥塞经历(Congestion Experienced CE)代码点。

如果与 ECT 代码点一起发送的 QUIC 数据包在没有 ECN 反馈的 ACK 帧中由对端新确认，
则终端停止在后续 IP 数据包中设置 ECT 代码点，期望网络路径或对端不再支持 ECN。

破坏或应用非标准 ECN 标记的网络设备可能会导致吞吐量降低或其他不希望的副作用。
为了降低这种风险，终端使用以下步骤来验证它在 ACK 帧中收到的计数。

* ECT(0)、ECT(1)和 CE 计数的总增加**必须**不小于与此 ACK 帧中新确认的 ECT 代码点一起发送的 QUIC 数据包的总数。
  此步骤检测来自 ECT(0)、ECT(1)或 CE 代码点指向非 ECT 的任何网络标记。

* ECT(0) 或 ECT(1)计数的任何增加，以及 CE 计数的任何增加，
  都**必须**不小于与此 ACK 帧中新确认的相应 ECT 代码点一起发送的数据包数量。
  此步骤检测从 ECT(0) 到 ECT(1) 的任何错误网络标记(反之亦然)。

当 ACK 帧丢失时，终端可能会错过对数据包的确认。
因此，ECT(0)、ECT(1) 和 CE 计数的总增加可能大于 ACK 帧中确认的分组数量。
发生这种情况时，如果验证成功，则**必须**增加本地参考计数以匹配 ACK 帧中的计数。

乱序处理计数可能会导致验证失败。
如果在分组编号低于先前接收的 ACK 帧的分组中接收到 ACK 帧，则端点**不应该**执行此验证。
基于乱序到达的 ACK 帧进行验证可能会导致不必要地禁用 ECN。

验证成功后，终端继续在后续数据包中设置 ECT 代码点，期望路径支持 ECN。

如果验证失败，则终端停止在后续 IP 数据包中设置 ECT 代码点，期望网络路径或对端不支持 ECN。

如果终端在传出的 IP 数据包上设置 ECT 代码点，并且由于没有来自对端的确认而遇到重传超时(参见{{QUIC-RECOVERY}})，
或终端如果有理由相信网络路径上的元素可能正在破坏 ECN 代码点，则可以停止在后续数据包中设置 ECT 代码点。
这样做允许连接对破坏 IP 报头中的 ECN 代码点或丢弃 IP 报头中具有 ECT 或 CE 代码点的数据包的网络元素具有适应能力。


# 包大小(Packet Size) {#packet-size}

QUIC 数据包大小包括 QUIC 报头和受保护的有效载荷，但不包括 UDP 或 IP 报头。

客户端**必须**确保发送单个 IP 数据包中的第一个初始数据包。
同样，在接收重试数据包后发送的第一个初始数据包**必须**在单个 IP 数据包中发送。

携带第一个初始包的 UDP 数据报的有效载荷**必须**通过向初始包添加填充帧和
/或通过将初始包与 0-RTT 包组合(参见{{packet-coalesce}})来扩展到至少1200字节。
发送此大小的 UDP 数据报可确保网络路径支持合理的最大传输单元(MTU)，
并有助于降低服务器对未经验证的客户端地址的响应所导致的放大攻击的幅度，参见{{address-validation}}。

如果客户端认为路径最大传输单元(PMTU)支持其选择的大小，则包含来自客户端的第一个初始数据包的数据报**可能**超过1200字节。

如果 UDP 数据报小于1200字节，则响应于它从客户端接收到的第一个初始包，
服务器**可以**发送错误代码为 PROTOCOL_VIOLATION 的 CONNECTION_CLOSE 帧。
它**禁止**发送任何其他帧类型作为响应，否则会表现为似乎有问题的数据包的任何部分被处理为有效一样。

在验证客户端地址之前，服务器还**必须**限制其发送的字节数，请参见{{address-validation}}。


## 路径最大传输单元(Path Maximum Transmission Unit) (PMTU)

PMTU 是整个 IP 数据包的最大大小，包括 IP 报头、UDP 报头和 UDP 有效负载。
UDP 有效负载包括 QUIC 数据包头、受保护的有效负载和任何身份验证字段。
PMTU 可以依赖于当前路径特性。
因此，实现将发送的当前最大 UDP 有效负载称为 QUIC最大包大小(QUIC Maximum Packet Size)。

QUIC 依赖于至少1280字节的PMTU。
这是 IPv6 最小大小{{?RFC8200}}，大多数现代 IPv4 网络也支持这一点。
所有 QUIC 数据包(PMTU探测数据包除外)的大小都**应该**调整为适合最大数据包大小，以避免数据包被分段或丢弃{{?RFC8085}}。

终端**应该**使用数据报包化层 PMTU 发现({{!DPLPMTUD=I-D.ietf-tsvwg-datagram-plpmtud}})或
实现路径 MUT发现(PMTUD){{!RFC1191}} {{!RFC8201}}，以判定到目的地的路径是否支持所需的消息大小而不会出现分段。

在没有这些机制的情况下，QUIC 终端**不应该**发送大于1280字节的 IP 数据包。
假设最小 IP 报头大小，这将导致 IPv6 的 QUIC 最大数据包大小为1232字节，IPv4 的最大数据包大小为1252字节。
QUIC 实现在计算 QUIC 最大分组大小时**可能**更为保守，以允许未知的隧道开销或 IP 报头选项/扩展。

每对本地和远程地址可以具有不同的 PMTU。
因此，实施任何类型的 PMTU 发现的 QUIC 实现**应该**为每个本地和远程 IP 地址组合保持最大数据包大小。

如果 QUIC 终端确定任何一对本地和远程 IP 地址之间的 PMTU 已降至支持允许的最小最大数据包大小所需的大小以下，
则它**必须**立即停止在受影响路径上发送 QUIC 数据包(PMTU 探测数据包除外)。
如果找不到替代路径，则终端**可以**终止连接。


## ICMP 包太大消息(ICMP Packet Too Big Messages) {#icmp-pmtud}

PMTU发现{{!RFC1191}} {{!RFC8201}} 依赖于
暗示因为比本地路由MTU大丢包的 IMCP 消息的接
收。(例如: IPv6 包太大消息)
DPLPMTUD 也可选的使用这些信息。
ICMP 消息的这种应用可能容易受到路境外攻击，
这些攻击成功猜测到了路径上使用的地址，
并且使 PMTU 降低到带宽低效值。

终端**必须**无视要求 PMTU 降低到
1280 字节 以下的 ICMP 消息。

生成 ICMP({{?RFC1812}}, {{?RFC4443}}) 的要求说明
所引用包应该在不超过对于这个 IP 版本的最小 MTU 的情况下
尽可能多的包含原包。
所引用包的大小实际上可以更小，
或者是不可理解的信息，如 {{!DPLPMTUD}} 1.1章节中的描述。

QUIC 终端**应该**校验 ICMP 消息来防止在
{{!RFC8201}}以及{{!RFC8085}}中5.2章节
中指出的路境外注入。
这个验证**应该**使用在 ICMP 消息载荷中提供的
所引用包来联系这条消息与相对于的传输连接 {{!DPLPMTUD}}。

ICMP 消息校验**必须**包括匹配 IP 地址和
UDP 端口{{!RFC8085}}，可能的话，
还要包括对应一个活动的QUIC会话的连接 ID。

可以提供如下更多的校验：

* IPv4 终端可能在小比例的包中设置禁止分片(DF)位，
以便当没有DF的包未处理时，
若大部分的不可用的 ICMP 消息抵达了，
然后这些包因此可能被鉴定为可疑的。

* 终端可以存储 IP 或者 UDP 包头中的附加信息用于
校验(例如，IP IP 或者 UDP 校验和)。

终端**应该**无视所有的校验不通过的 ICMP 消息。

终端**禁止**基于 ICMP 消息增大 PMTU 。
直到 QUIC 丢包检测算法确定所引用包已经丢失为止，
任何 QUIC 最大包大小的减小都**可能**是暂时的。


## 数据包包装层 PMTU 发现(Datagram Packetization Layer PMTU Discovery)

{{!DPLPMTUD}}中 6.4 章节中提供了实现
QUIC 数据包装层 PMTUD (DPLPMTUD)的思考。

当实现在{{!DPLPMTUD}}中5.3章节描述的算法时候，
BASE_PMTU的初始值**应该**和最小 QUIC 包大小一致。
(IPv6为1232 字节而 IPv4位1252字节)

PING 和 PADDING 帧可用于生成 PMTU 探测包。
如果包含他们的探测包丢失，这些帧可能不会重传。
然而，这些帧确实消费了拥塞窗口，
这可能会延迟子流应用数据的传输。

PING帧可以被包含在一个 PMTU 探测中，
用于确保一个可用的探测已经被确认了。

如果这些消息被 DPLPMTUD 使用，
则在之前的章节关于处理 ICMP 消息的思考也适用。


# 版本(Versions) {#versions}

QUIC 版本用一个32位的无符号整数标识。

版本 0x00000000 保留用于代表版本协商。
这个特定的版本用 0x00000001 来标识。

其他版本的 QUIC 可能有和此版本不同的属性。
QUIC保证在所有协议版本中都一致的属性描述在
{{QUIC-INVARIANTS}}中。

版本 0x00000001 的 QUIC 使用 TLS 作为
加密握手协议，如{{QUIC-TLS}}中所描述。

版本号中最高16位被清除的版本将保留
用于未来 IETF 协商一致的文档。

遵循0x?a?a?a?a规律的版本保留用于将要实践的强制版本协商。
这是说，任何所有比特中的低四位是1010(二进制)的版本号。
客户端或者服务器**可以**建议支持这些保留的任意版本。

保留的版本号可能永远不代表一个真实的协议；
客户端**可以**在预期服务端将初始化版本协商
的情况下使用这些中任意一个；
服务端**可以**建议支持这些版本中的一个，
并且预期客户端会无视这个值。

\[\[RFC 编辑者: 请在发布之前删除此章节。]]

此草案的最终版本号为0x00000001，
保留此版本用于此草案作为 RFC 公布时的版本。

用于标识 IETF 草案的版本号可用
草案数字加上0xff000000得到。
例如draft-ietf-quic-transport-13
可能标识为 0xff00000D.

实现鼓励注册用于私有实验的QUIC的版本号
到Github wiki，地址为
\<https://github.com/quicwg/base-drafts/wiki/QUIC-Versions\>.


# 可变长度数字编码(Variable-Length Integer Encoding) {#integer-encoding}

QUIC 包和帧通常对非负整数使用可变长度编码。
这种编码确保了小整数值需要更少的空间来编码。

QUIC 可变长度整数编码保留了第一个字节的两个最高有效位，
用于保存对整数长度取以2为底数的对数。
整数值以网络字节顺序编码在剩余位中。

这意味着整数编码成了1, 2, 4或者8字节，
对应编码了6, 14, 30或者62位的值。
{{integer-summary}}概括了编码规则。

| 2Bit | Length | Usable Bits | Range                 |
|:-----|:-------|:------------|:----------------------|
| 00   | 1      | 6           | 0-63                  |
| 01   | 2      | 14          | 0-16383               |
| 10   | 4      | 30          | 0-1073741823          |
| 11   | 8      | 62          | 0-4611686018427387903 |
{: #integer-summary title="编码规则概括"}

例如，八字节序列c2 19 7c 5e ff 14 e8 8c(十六进制)
解码为十进制值151288809941952652；
四字节序列9d 7f 3e 7d解码为494878333;
二字节序列7b bd解码为15293;
单字节序列25解码为37。(同二字节序列40 25的值)


错误编码({{error-codes}})和版本
{{versions}}使用整数描述，但不使用这种编码。



# 包格式（Packet Formats） {#packet-formats}

所有数字以大端法编码，
所有字段大小均以位为单位。
使用十六进制描述字段的值。


## 包编号的编码和解码（Packet Number Encoding and Decoding） {#packet-encoding}

包编号是从0到2^62-1的数字（{{packet-numbers}}）。
在长或短包头中，以1到4个字节进行编码。
通过包含包编号的最低有效位来减少
其所需的字节数。

编码后的包编号使用5.4章中描述的{{QUIC-TLS}}
进行保护。

发送方**必须**必须预留足够大的包编号范围，这个范围必须是
最大的已确认包的编号大小和已发送包数量的
两倍。接收包的对端将正确的解码该包编号，
除非该包延迟了，使得它
在许多较高编号的包之后到达。终端
**应该**使用足够大的包编号编码，以允许包编号被接收，
即使是此包在它之后发送的包之后才到达。

所以，包编号编码的大小至少比包含新包在内的连续的
未确认的包数量的以2为底的对数多一位。
log2(len(包含新包在内的连续的未确认的包))+1。

例如，如果一个终端收到了0xabe8bc包的确认，
在发送编号为0xac5c02的包的时候需要16位以上
的包编号编码；发送编号为0xace8fe就需要24位
包编号编码。

在接收方，在恢复完整的包编号之前要移除对包编号
的保护。然后，根据存在的有效位的数量、这些位的
值以及在成功验证的数据包上接收的最大数据包数，
重新构造完整的数据包号。成功移除包保护依赖于
恢复完整的包编号。

一旦包头保护被移除，就可以根据最接近下一个预期包的
包编号来解码包编号。下一个
预期的包是接收到的最高包编号加1。例如，如果
成功通过验证的包中最高包编号为0xa82f30ea，
包含16位编码0x9b32的包编码将被解码位0xa82f9b32。
包解码的为代码示例在
{{sample-packet-number-decoding}}中提供。


## 长包头数据包（Long Header Packets） {#long-header}

~~~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|1|1|T T|X X X X|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       版本（Version） (32)                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|DCIL(4)|SCIL(4)|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         目标连接ID（Destination Connection ID）(0/32..144)    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|               源连接ID（Source Connection ID）(0/32..144)     ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~
{: #fig-long-header title="长包头数据包格式"}

长包头用于那些遭遇建立1-RTT密钥的包。
满足两个条件后，
发送方切换到使用短包头来发送包
（{{short-header}}）。长格式允许特殊的包 - 比如
版本协商包 - 食用这样统一固定长度的
包格式。使用长包头的包包含如下字段：

头表单：

: 0字节（第一个字节）最高有效位（0x80）设置为1
  代表长包头。

固定位：

: 0字节中的下一个位（0x40）被设置成1。这一位为0
  的包在这个版本下是无效的并且**必须**被丢弃。

长包类型（T）：

: 0字节接下来的两位（0x30）包含包类型。
  包类型在{{long-packet-types}}中列举了。

类型限定位（X）：

: 0字节较低的4位（0x0f）是类型限定位。

版本：

: QUIC版本是一个紧跟着第一个字节的32位字段。这个字段
  标明了正在使用的QUIC版本，并标明了如何解释剩余
  的协议字段如何解释。

DCIL和SCIL：

: 紧接着版本之后的字节标明了两个链接ID
  字段的长度。这两个长度被编码位4位无符号
  证书。目标连接ID长度（DCIL）为高4位
  源连接ID长度（SCIL）
  为低4位。0值表示
  连接ID的长度是0字节。非0值
  需要加3以获取连接ID的完整长度，ID长度
  在4到18字节（包含4和18）之间。例如，0x50这个字节
  描述了目标连接ID长度位8为，
  源连接ID长度为0。

目标连接ID：

: 目标连接ID字段紧接着ID长度字段，它
  可能是0字节或者4到18字节长。
  {{negotiating-connection-ids}}描述了更多此字段的细节。

源连接ID：

: 源连接ID字段紧跟着目标连接ID字段，它
  也是0字节或者4到18字节长。
  {{negotiating-connection-ids}}描述了更多关于此字段的细节。

如下给出了在此版本的QUIC中长包头包中类型的
定义：

| 类型  | 名称                          | 章节                         |
|-----:|:------------------------------|:----------------------------|
|  0x0 | Initial                       | {{packet-initial}}          |
|  0x1 | 0-RTT                         | {{packet-0rtt}}             |
|  0x2 | Handshake                     | {{packet-handshake}}        |
|  0x3 | Retry                         | {{packet-retry}}            |
{: #long-packet-types title="长包头包类型"}

长包头当中描述连接ID长度的字段、目标和源地址的字段
以及版本字段
是版本无关的。第一个字节中其他的字段是版本特殊的。
参考{{QUIC-INVARIANTS}}中描述的不同版本的QUIC
是如何解释包格式的。

字段和有效负载的解释在各个版本和包类型之间是
不同的。以下各节介绍了
此版本的特殊信息，此版本的QUIC中一些长包头包
包含额外的字段。

保留位（R）：

: 0字节中的两位（0x0c）是跨包类型
  保留的。这些位使用包头保护进行保护（参见章节
  5.4{{QUIC-TLS}}）。这个字段的原是值必须是0。
  如果终端在移除包和包头保护之后发现此字段为非0值，
  则终端**必须**将这种情况视为PROTOCOL_VIOLATION
  类型的连接错误。在仅移除包头包头保护之后丢弃
  这样的包可能导致终端收到攻击
  （参见章节9.3{{QUIC-TLS}}）。

包编号长度（P）：

: 在包含包编号字段的包中，0字节的最低两个有效
  位（0x03）包含包编号的长度。
  编码位2位无符号整数，次整数比包编
  号的长度小1。也就是说，包编号字段的
  长度是此字段的值加1。这些位使用
  包头保护进行保护（参见5.4{{QUIC-TLS}}）。

长度：

: 包中剩下的部分（包编号和有效负载字段）
  以字节为单位的长度，编码为可变长度的整数
  （{{integer-encoding}}）。

包编号：

: 包编号字段的长度为1到4字节。包编号具有独立于
  包保护的机密性保护，如章节5.4{{QUIC-TLS}}
  中描述的。包编号字段的长度被编码在字节0的
  包编号位中（见上文）。

### 版本协商包(Version Negotiation Packet) {#packet-version}

版本协商包本质上不是特定于版本的。
客户端收到后，将根据Version字段的值为0将其标识为版本协商包。

版本协商包是对客户机包的响应，
客户机包包含服务器不支持的版本，并且只由服务器发送。

版本协商包的布局为:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|1|  未使用位(Unused) (7) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          版本位(Version) (32)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|DCIL(4)|SCIL(4)|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|               目标连接ID(Destination Connection ID) (0/32..144)         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                 源连接ID(Source Connection ID) (0/32..144)            ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    支持的版本1(Supported Version 1) (32)                 ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   支持的版本2([Supported Version 2 (32)])                ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
                               ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   支持的版本N([Supported Version N (32)])                ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #version-negotiation-format title="版本协商包(Version Negotiation Packet)"}

未使用字段中的值由服务器随机选择。

版本协商包的版本字段**必须**设置为0x00000000。

服务器**必须**在目标连接ID字段中包含它接收的包的源连接ID字段的值。
源连接ID的值**必须**从接收包的目标连接ID复制，该包最初是由客户机随机选择的。
响应这两个连接id可以向客户端保证服务器收到了数据包，
并且版本协商包不是由偏离路径的攻击者生成的。

版本协商包的其余部分是服务器支持的32位版本列表。

版本协商包不能在ACK帧中被客户机显式地确认。
接收另一个初始包隐式地确认一个版本协商包。

版本协商包不包括使用长头表单的其他包中出现的包号和长度字段。
因此，版本协商包使用整个UDP数据报。

服务器**禁止**发送多个版本协商包来响应单个UDP数据报。

有关版本协商过程的描述，请参见{{version-negotiation}}。

### 初始数据包(Initial Packet) {#packet-initial}

初始包使用类型值为0x0的长头。
它携带客户端和服务器发送的第一个CRYPTO帧来执行密钥交换，并携带两个方向的ACK。

~~~
+-+-+-+-+-+-+-+-+
|1|1| 0 |R R|P P|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         版本(Version) (32)                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|DCIL(4)|SCIL(4)|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|               目标连接ID(Destination Connection ID) (0/32..144)         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                 源连接ID(Source Connection ID) (0/32..144)            ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         令牌长度(Token Length) (i)                    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                            令牌(Token) (*)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           长度(Length) (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    包号(Packet Number) (8/16/24/32)               ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          有效载荷(Payload) (*)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #initial-format title="初始数据包(Initial Packet)"}

初始包包含一个长报头以及长度和包号字段。
第一个字节包含保留的和包号长度位。
在SCID和Length字段之间，有两个特定于初始包的附加字段。

令牌长度(Token Length):

: 指定令牌字段长度(以字节为单位)为可变长度整数。
  如果不存在令牌，则此值为零。服务器发送的初始数据包**必须**将令牌长度字段设置为零;
  接收具有非零令牌长度字段的初始数据包的客户机**必须**丢弃该数据包
  或生成类型为PROTOCOL_VIOLATION的连接错误。

令牌(Token):

: 令牌的值是由之前的重试包或NEW_TOKEN帧中提供的。

有效载荷(Payload):

: 数据包的有效载荷。

为了防止不知道版本的中间件的篡改，
初始数据包被连接和特定于版本的密钥(初始密钥)保护，如 {{QUIC-TLS}}中所述。
此保护不提供对路径上攻击者的机密性或完整性的保护，
但提供了对偏离路径攻击者的某种级别的保护。

客户机和服务器对包含初始加密握手信息的任何包使用初始包类型。
这包括所有需要创建包含初始加密消息的新包的情况，
例如接收重试包后发送的包 ({{packet-retry}})。

服务器发送它的第一个初始包作为对客户机初始包的响应。
服务器可以发送多个初始包。密码的密钥交换可能需要多次往返或重新传输数据。

初始包的有效负载包括包含加密握手信息、ACK帧或两者都包含的CRYPTO帧(或多个帧)。
也允许PADDING和CONNECTION_CLOSE帧。
接收包含其他帧的初始包的终端可以将该包作为伪包丢弃，也可以将其视为连接错误。

客户端发送的第一个数据包总是包含一个含有第一个加密握手消息全部内容的CRYPTO帧。
这个数据包和加密握手信息**必须**包含在一个UDP数据报中(见{{handshake}})。
发送的第一个CRYPTO帧总是以偏移量0开始(见{{handshake}})。

注意，如果服务器发送一个HelloRetryRequest，客户机将发送第二个初始包。
这个初始包将继续加密握手，并将包含一个与第一个初始包中发送的CRYPTO帧
大小匹配的偏移量的CRYPTO帧。
第一次握手之后的加密握手信息不需要包含在一个UDP数据报中。

#### 丢弃初始数据包(Abandoning Initial Packets) {#discard-initial}

客户端在发送第一个握手包时停止发送和处理初始数据包。
当服务器接收到它的第一个握手包时停止发送和处理初始数据包。
虽然数据包可能仍然在传输或等待确认，但在此之后不需要再互相传输任何初始包。
初始包保护密钥，(参见{{QUIC-TLS}}第4.10节)，
任何丢失恢复和拥塞控制状态都将被丢弃(参见{{QUIC-RECOVERY}}第5.3.1.2节和6.9节)。

当初始密钥被丢弃时，CRYPTO帧中的任何数据都将被丢弃，并且不再重新传输。


### 0-RTT {#packet-0rtt}

0-RTT数据包使用类型值为0x1的长报头，后跟长度和数据包号字段。第一个字节包含保留和数据
包号长度位。它用于在握手完成之前，将“早期”数据从客户端传送到服务器，作为第一次传输的
一部分。作为TLS握手的一部分，服务器可以接受或拒绝此早期数据。

有关0-RTT数据及其限制的讨论，请参见{{!TLS13}}的2.3节。

~~~
+-+-+-+-+-+-+-+-+
|1|1| 1 |R R|P P|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         版本 (32)                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|DCIL(4)|SCIL(4)|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     目标链接编号 (0/32..144)                ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    源链接编号 (0/32..144)                   ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           长度 (i)                          ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      包号 (8/16/24/32)                      ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          负载 (*)                           ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #0rtt-format title="0-RTT 包"}


0-RTT保护数据包的数据包号与1-RTT保护数据包使用相同的空间。

客户端收到重试数据包后，0-RTT数据包可能已丢失或被服务器丢弃。客户端在发送新的初始数据
包后，**可能**会尝试在0-RTT数据包中重新发送数据。

客户端**禁止**重置其用于0-RTT数据包的数据包号。用于保护0-RTT数据包的密钥不会因响应重试数据
包而更改，除非客户端也重新生成加密握手消息。在这种情况下，发送具有相同数据包号的数据包
可能会损害所有0-RTT数据包的数据包保护，因为相同的密钥和nonce可用于保护不同的内容。

接收重试数据包，特别是更改用于后续数据包的连接ID的重试，表示0-RTT数据包丢失的可能性很大。
只有在握手完成后，客户端才会收到对其0-RTT数据包的确认。因此，服务器可能期望0-RTT数据包从
数据包编号0开始。因此，在确定0-RTT数据包编码的数据包号长度时，客户端必须假设当前数据包号
之前的所有数据包都在运行，从数据包号0开始。因此，0-RTT数据包可能需要使用更长的数据包编号
编码。

相反，客户端**应该**生成一个新的加密握手消息，并从0开始数据包号。这确保了新的0-RTT数据包不会
使用相同的密钥，从而避免了密钥和一次性重复使用的任何风险；这还可以防止以前的握手尝试将
0-RTT数据包作为连接的一部分接受。


### 握手数据包(Handshake Packet) {#packet-handshake}

握手数据包使用类型值为0x2的长报头，后跟长度和数据包号字段。第一个字节包含保留和数据包号
长度位。它用于传送来自服务器和客户端的确认和加密握手消息。

~~~
+-+-+-+-+-+-+-+-+
|1|1| 2 |R R|P P|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           版本 (32)                           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|DCIL(4)|SCIL(4)|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     目标链接编号 (0/32..144)                 ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    源链接编号 (0/32..144)                    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           长度 (i)                          ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      包号 (8/16/24/32)                      ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          负载 (*)                           ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #handshake-format title="握手保护包"}

一旦客户端从服务器收到握手数据包，它就会使用握手数据包向服务器发送后续加密握手消息和
确认。

握手包中的目的地连接ID字段包含由包的接收者选择的连接ID; 源连接ID包括数据包发送方希望
使用的连接ID（参见{{negotiating-connection-ids}}）。

握手包是它们自己的包号空间，因此服务器发送的第一个握手包中包含的包号为0。

该数据包的有效负载包含CRYPTO帧，可能包含PADDING或ACK帧。 握手包**可能**包含
CONNECTION_CLOSE帧。 对端**必须**将包含其他帧的握手数据包视为连接错误。。

与初始数据包(参见{{discard-initial}})一样，握手加密级别的CRYPTO帧中的数据在丢弃握
手保护密钥时将被丢弃，且不再重新传输。

### 重试包(Retry Packet) {#packet-retry}

重试数据包使用类型值为0x3的长数据包报头。它携带由服务器创建的地址验证令牌。它由希望
执行无状态重试的服务器使用(请参见{{validate-handshake}})。


~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|1|1| 3 | ODCIL |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         版本(32)                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|DCIL(4)|SCIL(4)|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      目标连接ID (0/32..144)                  ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      源连接ID (0/32..144)                    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   原始目标连接ID(0/32..144)                  ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          重试令牌(*)                         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #retry-format title="Retry Packet"}

重试数据包(如{{retry-format}}所示)不包含任何受保护的字段。除了长标头之外，它还包
含以下附加字段：

ODCIL:

: 由于重试数据包不包含受保护的有效负载，因此与其他具有长头的数据包一样，重试数据包第
  一个字节的四个最低有效位不受保护。这些位改为对原始目标连接ID字段的长度进行编码。长
  度使用与DCIL和SCIL字段相同的编码。

原始目标连接ID:

: 原始目标连接ID包含此重试响应的初始数据包中的目标连接ID的值。此字段的长度在ODCIL中
  给出。

重试令牌:

: 服务器可用于验证客户端地址的不透明令牌。

<!-- Break this stuff up a little, maybe into "Sending Retry" and "Processing
Retry" sections. -->

服务器用客户端在初始数据包的源连接ID中包含的连接ID填充目标连接ID。

服务器在源连接ID字段中包含其选择的连接ID。此值**不能**等于客户端发送的数据包的目标连接ID
字段。客户端**必须**在其发送的后续数据包的目标连接ID中使用此连接ID。

服务器**可以**发送重试数据包以响应初始数据包和0-RTT数据包。服务器可以丢弃或缓冲它接收的
0-RTT数据包。当服务器接收到初始或0-RTT数据包时，可以发送多个重试数据包。服务器**不能**
发送多个重试数据包以响应单个UDP数据报。

对于每次连接尝试，客户端**必须**最多只能接受并处理一个重试数据包。客户端接收并处理来自服
务器的初始或重试数据包后，**必须**丢弃其接收的任何后续重试数据包。

客户端**必须**丢弃包含原始目标连接ID字段与初始数据包的目标连接ID不匹配的重试数据包。这可
防止非路径攻击者注入重试数据包。

客户端用包含提供的重试令牌的初始数据包响应重试数据包，以继续建立连接。

客户端将此初始数据包的目标连接ID字段设置为重试数据包中源连接ID的值。更改目标连接ID也会导
致用于保护初始数据包的密钥发生更改。它还将令牌字段设置为重试中提供的令牌。客户端**禁止**
更改源连接ID，因为服务器可以将连接ID作为其令牌验证逻辑的一部分(请参见{{token-integrity}})。

来自客户端的下一个初始数据包使用来自重试数据包的连接ID和令牌值
（请参见{{negotiating-connection-ids}}）。除此之外，客户端发送的初始数据包受与第一个初
始数据包相同的限制。客户机既可以重用加密握手消息，也可以自行构建新的握手消息。

客户端在收到重试数据包后，**可以**通过向服务器提供的连接ID发送0-RTT数据包来尝试0-RTT。
如果客户端发送额外的0-RTT数据包而不构造新的加密握手消息，则在重试数据包后，**禁止**将
数据包编号重置为0，请参见{{packet-0rtt}}。

服务器确认使用original_connection_id传输参数对连接使用重试数据包(请参见
{{transport-parameter-definitions}})。如果服务器发送重试数据包，则**必须**在传输参
数中包含重试数据包的原始目标连接ID字段的值(即客户端第一个初始数据包中的目标连接ID字段)。

如果客户端接收并处理了一个重试包，它**必须**验证原original_connection_id传输参数是否存在且
正确；否则，它**必须**验证传输参数是否缺失。客户端**必须**将失败的验证视为
TRANSPORT_PARAMETER_ERROR类型的连接错误。

重试数据包不包含数据包编号，并且无法由客户端明确确认。

## 短包头的包（Short Header Packets） {#short-header}

此版本的QUIC协议定义了使用短数据包头的单个包类型。
This version of QUIC defines a single packet type which uses the
short packet header.

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|0|1|S|R|R|K|P P|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                Destination Connection ID (0..144)           ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Packet Number (8/16/24/32)              ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Protected Payload (*)                   ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~
{: #fig-short-header title="Short Header Packet Format"}

短包头能在版本协商和1-RTT秘钥协商包后面的
包上使用。使用短包头的包中包含了以下的这些字段：

头部组成:

: 短包头包的第0字节中的最高有效位(0x80)设置为0

固定位:

: 第0字节的下一位(0x40)设置为1。
在当前版本的协议中规定了，该位被设置为0的
包不是有效包**必须**丢弃。

自旋位 (S):

: 第一个字节的第六位(0x20)是延迟自旋位，
该位的取值参考{{!SPIN=I-D.ietf-quic-spin-exp}}。

保留位 (R):

: 第0个字节的后面两个位(掩码为0x18的位)将被保留。
这些位会使用包头保护进行保护(请参阅第5.4节{{QUIC-TLS}})。
在添加保护之前的值**必须**设置为0。终端在移除
接收到的包的包和头部保护后，**必须**将
保留位具有非零值的包视
为PROTOCOL_VIOLATION类型的连接错误。
在仅移除包头保护后就丢弃这样的包可能会使
终端受到攻击。(参考9.3节关于{{QUIC-TLS}})。

秘钥段 (K):

: 第0字节的下一位(0x04)用于指示秘钥段，
这一位可以使包的接受者识别用于保护包的包保护秘钥。
详情请阅{{QUIC-TLS}}。该位处于包头保护之下
（参考5.4节关于{{QUIC-TLS}})。


包编号长度 (P):

: 第0字节的最低有效两位(掩码为0x03)放置了包编号的长度，
包编号的长度被编码为两位无符号整型，该整型小于
包编号字段的长度(以字节为单位)。
也就是说，包编号字段的长度是该字段的值加1。
这些位处于包头保护之下(请参阅第5.4节{{QUIC-TLS}})。

目标连接ID:

: 目标连接ID是包的目标接收方选择的连接ID。
详细信息请参见{{connection-id}}。

包编号:

: 包编号字段的长度为1到4个字节。
包编号具有独立于包保护的机密性保护，
如{{QUIC-TLS}}第5.4节所述。
包编号字段的长度编码在包编号长度字段中。
详细信息请参见{{packet-encoding}}。

被保护的负载:

: 短包头的包始终包含受1-RTT保护的有效负载。

短包头包的包头组成位和连接ID字段的
取值与协议版本无关。其余字段特定于
选定的QUIC版本。关于如何解释
来自不同版本QUIC的包的详细信息，请参见{{QUIC-INVARIANTS}}。


# 传输参数编码（Transport Parameter Encoding） {#transport-parameter-encoding}

传输参数的格式是{{figure-transport-parameters}}中的
TransportParameters结构。
{{!TLS13=RFC8446}}第3节中使用演示语言对此进行了描述。

~~~
   enum {
      original_connection_id(0),
      idle_timeout(1),
      stateless_reset_token(2),
      max_packet_size(3),
      initial_max_data(4),
      initial_max_stream_data_bidi_local(5),
      initial_max_stream_data_bidi_remote(6),
      initial_max_stream_data_uni(7),
      initial_max_streams_bidi(8),
      initial_max_streams_uni(9),
      ack_delay_exponent(10),
      max_ack_delay(11),
      disable_migration(12),
      preferred_address(13),
      (65535)
   } TransportParameterId;

   struct {
      TransportParameterId parameter;
      opaque value<0..2^16-1>;
   } TransportParameter;

   TransportParameter TransportParameters<0..2^16-1>;
~~~
{: #figure-transport-parameters title="Definition of TransportParameters"}

在{{QUIC-TLS}}中定义的quic_transport_parameters
扩展的“EXTENSION_DATA”字段包含TransportParameters值。
因此，TLS编码规则被用来描述传输参数的编码。

QUIC将传输参数编码为字节序列，然后
将其放置在加密握手包中。


## 传输参数定义(Transport Parameter Definitions) {#transport-parameter-definitions}

本节详细介绍了本文档中定义的传输参数。

此处列出的许多传输参数都具有整数值。
除非另有说明，否则标识为整数的传输参数使用
可变长度整数编码（请参阅{{integer-encoding}}），
如果传输参数不存在，则默认值为0。

传输参数有以下定义：

original_connection_id (0x0000):

: 客户端发送的第一个Initial数据包中的
  Destination Connection ID字段的值。
  此传输参数仅由服务器发送。
  如果服务器发送了重试数据包，
  则**必须**包含original_connection_id传输参数。

idle_timeout (0x0001):

: 空闲超时是以毫秒为单位的值，编码为整数,
  参考({{idle-timeout}})。
  如果此参数不存在或为零，则禁用空闲超时。

stateless_reset_token (0x0002):

: 无状态重置令牌用于验证无状态重置, 参考{{stateless-reset}}。
  该参数是16个字节的序列。
  此传输参数仅由服务器发送。

max_packet_size (0x0003):

: 最大数据包大小参数是一个整数值，
  用于限制终端愿意接收的数据包的大小。
  这表示将丢弃大于此限制的数据包。
  此参数的默认值是UDP允许的最大有效负载65527，
  低于1200的值无效。
  此限制仅适用于受保护的数据包（参考{{packet-protected}}）。

initial_max_data (0x0004):

: 初始最大数据参数是一个整数值，
  包含可以在连接上发送的最大数据量的初始值。
  这相当于在完成握手后立即为连接发送MAX_DATA
  （{{frame-max-data}}）。

initial_max_stream_data_bidi_local (0x0005):

: 此参数是一个整数值，
指定本地启动的双向流的初始流量控制限制。此
限制适用于由发送传输参数的终端打开的新创建的双向流。
在客户端传输参数中，
这适用于最低有效两位设置为0x0的流;
在服务器传输参数中，
这适用于最低有效两位设置为0x1的流。

initial_max_stream_data_bidi_remote (0x0006):

: 此参数是一个整数值，
  指定对等启动的双向流的初始流控制限制。
  此限制适用于由接收传输参数的终端打开的
  新创建的双向流。
  在客户端传输参数中，
  这适用于最低有效两位设置为0x1的流;
  在服务器传输参数中，
  这适用于最低有效两位设置为0x0的流。

initial_max_stream_data_uni (0x0007):

: 此参数是一个整数值，指定单向流的初始流控制限制。
  此限制适用于由接收传输参数的终端
  打开的新创建的单向流。
  在客户端传输参数中，
  这适用于最低有效两位设置为0x3的流;
  在服务器传输参数中，
  这适用于最低有效两位设置为0x2的流。

initial_max_streams_bidi (0x0008):

: 初始最大双向流参数是整数值，
  其包含对端可以发起的初始最大双向流数量。
  如果此参数不存在或为零，则在发送MAX_STREAMS帧之前，
  对等方无法打开双向流。
  设置此参数等效于发送具有相同值的
  相应类型的MAX_STREAMS（{{frame-max-streams}}）。

initial_max_streams_uni (0x0009):

: 初始最大单向流参数是整数值，
  其包含对端可以发起的初始最大单向流数。
  如果此参数不存在或为零，则对等方无法打开单向流，
  直到发送MAX_STREAMS帧为止。
  设置此参数等效于发送具有相同值的相应类型
  的MAX_STREAMS（{{frame-max-streams}}）。

ack_delay_exponent (0x000a):

: ACK延迟指数是指示用于解码ACK帧中的
  ACK延迟字段的指数的整数值（{{frame-ack}}）。
  如果此值不存在，则假定默认值为3（表示乘数为8）。
  默认值也用于在Initial和Handshake数据包中发送的ACK帧。
  大于20的值无效。

max_ack_delay (0x000b):

: 最大ACK延迟是一个整数值，
表示终端延迟发送前确认的最长时间（以毫秒为单位）。
该值应该包括接收者在警告发送时的预期延迟。
例如，如果接收者定时设置为5ms
并且警告通常会延迟最多1ms，
那么它应该发送6ms的max_ack_delay。
如果此值不存在，则假定默认值为25毫秒。
2 ^ 14或更大的值无效。

disable_migration (0x000c):

: 如果终端不支持连接迁移（{{migration}}），
  则包括该禁用迁移传输参数。
  设置了此传输参数的终端的对端**禁止**从除
  用于执行握手的本地地址之外的本地地址发送任何数据包，
  包括探测数据包（{{probing}}）。
  此参数是零长度值。

preferred_address (0x000d):

: 服务器的首选地址用于在握手结束时
  实现服务器地址的更改，
  参考{{preferred-address}}中的描述。
  此传输参数的格式是{{fig-preferred-address}}中
  显示的PreferredAddress结构。
  此传输参数仅由服务器发送。
  服务器**可能**选择为另一个地址族发送全0地址和端口
  （0.0.0.0:0或::.0）来实现仅发送一个地址族的首选地址。

~~~
   struct {
     opaque ipv4Address[4];
     uint16 ipv4Port;
     opaque ipv6Address[16];
     uint16 ipv6Port;
     opaque connectionId<0..18>;
     opaque statelessResetToken[16];
   } PreferredAddress;
~~~
{: #fig-preferred-address title="首选地址格式(Preferred Address format)"}

如果存在，则设置初始流控制限制的传输参数
（initial_max_stream_data_bidi_local，initial_max_stream_data_bidi_remote
和initial_max_stream_data_uni）
等同于在打开之后立即在相应类型的每个流上发送
MAX_STREAM_DATA帧（{{frame-max-stream-data}}）。
如果传输参数不存在，则该类型的流以流控制限制为0开始。

客户端**禁止**包含原始连接ID，
无状态重置令牌或首选地址。
服务器**必须**将任何这些传输参数的接收视为
TRANSPORT_PARAMETER_ERROR类型的连接错误。


# 帧类型和格式(Frame Types and Formats) {#frame-formats}

如 {{frames}}所述，数据包包含一个或多个帧。本节描述核心QUIC帧类型的格式和语义。

## 填充帧（PADDING Frame） {#frame-padding}

PADDING帧(类型=0x00)没有语义值。PADDING帧可以用来增加包的大小。
PADDING帧可用于将初始客户端包增加到所需的最小大小，或为受保护的包提供流量分析保护。

PADDING帧没有内容。也就是说，PADDING帧由一个字节组成，该字节将帧标识为PADDING帧。

## PING帧 （PING Frame） {#frame-ping}

终端可以使用PING帧(类型=0x01)来验证它们的对端是否仍然是活动状态，
或者检查对端的可达性。PING帧不包含其他字段。

PING帧的接收者只需要确认包含该帧的包。

当应用程序或应用程序协议希望防止连接超时时，可以使用PING帧保持连接处于活动状态。
应用程序协议**应该**提供关于建议生成PING的条件的指导。
此指南**应当**指示预期发送PING的是客户机还是服务器。
如果两个终端都发送PING帧而不进行协调，则会产生过多的数据包，并且性能很差。

如果没有发送或接收数据包的时间超过idle_timeout传输参数中指定的时间
(参见{{termination}})，连接将超时。
然而，在中间件中的状态可能会比这更早超时。
虽然{{?RFC4787}}中的REQ-5建议2分钟超时间隔，但经验表明，
每15到30秒发送包是必要的，以防止UDP流的大多数中间件丢失状态。


## ACK帧 （ACK Frames） {#frame-ack}

接收者发送ACK帧(类型为0x02和0x03)来通知发送者他们已经接收和处理了数据包。
ACK帧包含一个或多个ACK范围。ACK范围标识已确认的数据包。
如果帧类型是0x03, ACK帧还包含到目前为止在连接上接收到的带有相关ECN标记的QUIC包的和。
QUIC实现**必须**正确地处理这两种类型，如果它们为发送的包启用了ECN，
则**应该**使用ECN部分中的信息来管理它们的拥塞状态。

QUIC确认是不可撤销的。一旦确认，包就保持是确认的状态，即使它没有出现在未来的ACK帧。
这与TCP SACKs不同({{?RFC2018}})。

预计发送方将在不同的包号空间中重用相同的包号。
ACK帧只确认发送方在接收ACK的包的相同包号空间中传输的包号。

无法确认版本协商和重试包，因为它们不包含包号。
这些包不是依赖于ACK帧，而是由客户机发送的下一个初始包隐式地确认。

ACK帧如下:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|             最长确认位      Largest Acknowledged (i)          ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|             ACK 延迟      ACK Delay (i)                      ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|             ACK范围 计数         ACK Range Count (i)       ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|             首个ACK范围         First ACK Range (i)        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                 确认范围            (*)                     ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          [ECN 计数]                         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #ack-format title="ACK 帧格式"}

ACK帧包含以下字段：

Largest Acknowledged:

: 一个可变长度的整数，表示对端正在识别的最大包号;
  这通常是对端在生成ACK帧之前接收到的最大数据包号。
  与QUIC长报头或短报头中的包号不同，ACK帧中的值不会被截断。

ACK Delay:

: 一个可变长度的整数，包括发送此ACK时该对端接收到的最大已确认包的时间
  (如最大已确认字段中所示)(以微秒为单位)。
  ACK延迟字段的值通过将编码值乘以2的幂次乘以ACK帧
  的发送方设置的ack_delay_exponent传输参数的值来缩放。
  ack_delay_exponent默认值为3，或者乘数为8(参见{{transport-parameter-definitions}})。
  这种方式的缩放允许以较低的分辨率为代价，以更短的编码实现更大范围的值。

ACK Range Count:

: 一个可变长度整数，指定帧中间隔和ACK范围字段的数量。

First ACK Range:

: 一种变长整数，指示正在被确认的最大已确认包之前的连续数据包的数量。
  第一个ACK范围被编码为一个ACK范围(参见{{ack-ranges}})，从最大的已知范围开始。
  也就是说，范围内最小的确认包是由最大的确认包减去第一个ACK范围值来确定的。

ACK Ranges:

: 包含其他范围的数据包，
  这些数据包交替不被确认(Gap)和确认(ACK范围)，参见{{ack-ranges}}。

ECN Counts:

: 三个ECN计数, 见 {{ack-ecn-counts}}.


### ACK范围(ACK Ranges) {#ack-ranges}

“ACK范围”字段由按数据包编号降序排列的
“间隙”值和“ACK范围”值交替组成。
“间隙”(Gap)和“ACK范围”(ACK Range)值的数量
由“ACK范围计数”(ACK Range Count)字段确定；
ACK范围计数(Range Count)字段中的每个值都对应一个值。

ACK范围结构如下组织:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           [Gap (i)]                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          [ACK Range (i)]                    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           [Gap (i)]                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          [ACK Range (i)]                    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
                               ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           [Gap (i)]                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          [ACK Range (i)]                    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #ack-range-format title="ACK范围(ACK Ranges)"}

新城ACK范围的字段有:

间隙(重复的):

: 一个变长整数，表示比在之前的ACK范围中
最小包编号小一的连续未确认包的编号。

ACK 范围(重复的):

: 一个变长整数，表示小于当前最大包编号连续
确认包的编号，由之前的Gap确定。

间隙和ACK范围值使用相对整数编码以提高效率。
尽管每个编码的值都是正的，由于该值是被减去的，
所以每个ACK范围描述了编码降序的数据包。

每个ACK范围通过指示在该范围内最大数据包编号之前的
已确认数据包的编号来确认连续的数据包范围。
值为零表示仅确认最大的数据包号。
较大的ACK范围值表示较大的范围，
该范围内最小的数据包编号对应较小的值。
因此，给定范围内的最大数据包编号，
最小值由以下公式确定:

~~~
   smallest = largest - ack_range
~~~

ACK范围确认了最小包编号和最大包编号之间的所有数据包。

ACK范围的最大值是通过累计减去
前面所有ACK范围和间隙的大小来确定的。

每个间隙表示了未确认的包的范围。
间隙中的包的编号比间隙字段的编码值大一。

间隙字段的值使用以下公式确定后续ACK范围的最大包编号值:

~~~
   largest = previous_smallest - gap - 2
~~~

如果任何计算出的包编号是负值，
终端**必须**生成一个FRAME_ENCODING_ERROR
类型的连接异常表示ACK帧中的错误。


### ECN计数(ECN Counts) {#ack-ecn-counts}

ACK帧使用最低有效位(即类型0x03)来指示ECN反馈，
并且在数据包的IP报头中报告收到的QUIC包的关联的ECN码点
ECN(0), ECT(1), 或者 CE。
ECN计数仅仅在ACK帧类型是0x03的时候存在。

只有ACK帧类型是0x03的时候，ECN计数才会被解析。
有三个ECN计数，如下表示：

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        ECT(0) Count (i)                     ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        ECT(1) Count (i)                     ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        ECN-CE Count (i)                     ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

三个ECN计数分别是：

ECT(0) 计数:
: 一个变长的整数，表示接收到的带有ECT(0)码点的包的总数。

ECT(1) 计数:
: 一个变长的整数，表示接收到的带有ECT(1)码点的包的总数。

CE 计数:
: 一个变长的整数，表示接收到的带有CE码点的包的总数。

ECN 计数对每个包编码空间进行独立的维护。

## RESET_STREAM帧(RESET_STREAM Frame) {#frame-reset-stream}

终端使用RESET_STREAM帧(类型=0x04)来立刻中断一个流。

在发送RESET_STREAM帧之后，
终端停止在标识的流上的数据包的传输与重传。
收到RESET_STREAM的终端可以丢弃
它在这个流上已经收到的任何数据。

在一个仅发送流上接收到RESET_STREAM帧的终端
**必须**以STREAM_STATE_ERROR异常来中断连接。

RESET_STREAM帧如下表示:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Stream ID (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Application Error Code (16)  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Final Size (i)                       ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

RESET_STREAM 帧包含下列字段:

流 ID(Stream ID):

: 一个变长整数，编码将要终止的流的ID。

应用协议错误码(Application Error Code):

: 一个十六位的应用协议错误码(详见{{app-error-codes}})
，表示为什么流要被关闭。

最终大小(Final Size):

: 一个变长整数，
表示以位为单位的发送者定义的流的最终大小。

## STOP_SENDING帧（STOP_SENDING Frame） {#frame-stop-sending}

终端使用STOP_SENDING帧（类型标记为0x05）来告诉发送方应用程序要求
丢弃传入的数据。STOP_SENDING要求
对端停止在流当中的传输。

STOP_SENDING帧可以在状态为Rec和Size Known的流当中发送
（详见{{stream-send-states}}）。在一个本地初始化之后但
还未创建的流中收到STOP_SENDING帧**必须**引发
STREAM_STATE_ERROR类型的连接异常。终端在一个仅
接收的流中收到STOP_SENDING帧**必须**引发STREAM_STATE_ERROR
类型的连接异常。

STOP_SENDING帧如下说述：

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        流 ID (i)                            ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       应用程序错误码 (16)       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

STOP_SENDING帧包含如下字段

流ID：

: 可变长度的整数，表示被忽略的流ID。

应用程序错误码：

: 16位的，由应用程序指定的，发送方忽略此流的原因
  （详见{{app-error-codes}}）。


## CRYPTO帧（CRYPTO Frame） {#frame-crypto}

CRYPTO帧（类型标记为0x06）是用来传输加密握手信息的。
它可以被包含在所有类型的包当中被发送。CRYPTO帧为加密
协议提供了有顺序的字节流。CRYPTO帧和STREAM帧在
功能上相同，但是他们具有不同的流标示
符；他们不受流控制的限制；并且它们不包含
可选偏移、可选长度和流末端的标记。

CRYPTO帧如下所述：

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          偏移 (i)                           ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          长度 (i)                           ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Crypto Data (*)                      ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #crypto-format title="CRYPTO帧格式"}

CRYPTO帧包含如下字段：

偏移：

: 可变长度的整数，指定流中在此CRYPTO帧中的数据的
  偏移。

长度：

: 可变长度整数，指定此CRYPTO帧中Crypto Data字段的
  长度。

Crypto Data:

: 加密信息数据。

对于每一个加密级别有单独的加密
握手流，每个流都从偏移量0开始。这意味着每一个加密
级别都被视为单独的CRYPTO数据流。

CRYPTO帧不像STREAM帧那样含有用于指定数据属于那个流的
流ID，CRYPTO帧在每一个加密级别上为单个流
传输数据。流没有明确的结尾，所以CRYPTO帧没有
FIN位。


## NEW_TOKEN帧（NEW_TOKEN Frame） {#frame-new-token}

服务器通过NEW_TOKEN帧（类型标记为0x07）给客户端发送一个token，
这个token是用在以后连接的Initial包的包头的。

NEW_TOKEN帧结构如下：


~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Token 长度 (i)                      ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                            Token (*)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

NEW_TOKEN包含如下字段：

Token长度：

: 可变长度整数，表明token按位算的长度。

Token：

: 一个不透明的小玩意，客户端可能会用在以后的Initial包中。


## STREAM帧（STREAM Frames） {#frame-stream}

STREAM帧隐式的创建一个流并运送流数据。STREAM帧
采用0b00001XXX（或从0x08到0x0f的一组值）。
帧类型当中较低的3位标明了帧
当中存在的字段。

* OFF位（0x04）在帧类型中表明帧中有
  偏移字段。设置为1时，偏移字段存在。
  设置为0时，偏移字段不存在并且流数据从偏移0开始
  （也就是说，此帧包含这批流数据当中最开始的部分，或
  最后不包含数据的一部分。）

* LEN位（0x02）在帧类型中表明帧中有
  长度字段。设置为0时，长度字段不存在并且流数据
  字段延续到包的末尾。设置为1时，
  长度字段存在。

* FIN位（0x01）在帧类型中表明此帧包含此流
  最后的数据。此位被设置表明此帧
  标志着流的结束。

当一个终端从一个仅发送的流当中收到STREAM帧时，它**必须**关闭
连接并附带STEAM_STATE_ERROR错误。

STEAM帧结构如下：

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           流 ID (i)                         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           [偏移 (i)]                         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          [长度 (i)]                         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           流数据 (*)                         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #stream-format title="STREAM帧格式"}

STEREAM帧包含如下字段：

流ID：

: 可变长度的整数，标明此流的流ID（参见
{{stream-id}}）。

偏移：

: 可变长度整数，标明STREAM帧当中数据字段的
  偏移位。当OFF位设置为1时此字段存在。
  当偏移字段不存在时，偏移为0.

长度：

: 可变成都整数，标明STREAM帧中流数据字段
  的长度。当LEN位设置为1时此字段存在。当
  LEN位设置为0时，流数据占据了此包
  剩下的所有位。

流数据：

: 要传递的指定流中的字节。

当流数据字段的长度为0时，STREAM帧当中的偏移标明的是
下一个将要发送的位的偏移。

流的第一位的偏移为0。在流上传递的最大
偏移量 - 偏移量和数据长度之和 - **必须**小于2^62。


## MAX_DATA Frame帧(MAX_DATA Frame) {#frame-max-data}

在流控制中使用MAX_DATA帧(类型0x10)来通知对端连接上可以发送的最大数据量。

MAX_DATA帧如下:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       最大数据位数(Maximum Data) (i)                     ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

MAX_DATA帧包含以下字段:

最大数据量(Maximum Data):
  一个可变长度整数，以字节为单位，指示在整个连接上可以发送的最大数据量。

所有在STREAM帧中发送的数据都算下来都小于这个极限。所有流(包括处于终端状态的流)
上接收到的最大偏移量的总和**不得**超过接收方公布的值。
如果终端接收到的数据超过其发送的最大数据值，
则**必须**使用FLOW_CONTROL_ERROR错误终止连接，
除非这是初始限制更改的结果(请参阅{{zerortt-parameters}})。


## MAX_STREAM_DATA帧 (MAX_STREAM_DATA Frame) {#frame-max-stream-data}

在流控制中使用MAX_STREAM_DATA帧(类型=0x11)来通知对端在流上可以发送的最大数据量。

处于Recv状态的流可以发送MAX_STREAM_DATA帧(参见{{stream-send-states}})。
为尚未创建的本地发起的流接收MAX_STREAM_DATA帧**必须**被视为类型
为STREAM_STATE_ERROR的连接错误。
为仅接收流接收MAX_STREAM_DATA帧的终端**必须**使用错误STREAM_STATE_ERROR终止连接。

MAX_STREAM_DATA帧如下:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       流ID(Stream ID) (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   最大的流数据(Maximum Stream Data)(i)                  ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

MAX_STREAM_DATA帧包含以下字段:

流ID (Stream ID):

: 受影响的流的流ID编码为可变长度整数。

最大的流数据 (Maximum Stream Data):

: 一种可变长度整数，以字节为单位，指示可在标识的流上发送的最大数据量。

当将数据计数到这个极限时，终端占有流上发送或接收的数据的最大接收偏移量。
丢失或重新排序可能意味着流上接收到的最大偏移量可能大于该流上接收到的数据的总大小。
接收STREAM帧可能不会增加最大的接收偏移量。

在流上发送的数据**不能**超过接收方公布的最大的最大流数据值。
如果终端接收到的数据多于它为受影响的流发送的最大最大流数据值，
则必须使用FLOW_CONTROL_ERROR错误终止连接，
除非这是初始限制更改的结果(请参见{{zerortt-parameters}})。


## MAX_STREAMS(MAX_STREAMS Frames) {#frame-max-streams}

MAX_STREAMS帧(类型为0x12和0x13)通知对端打开允许的给定类型的流的累计数量。
类型为0x12的MAX_STREAMS帧应用于双向流，类型为0x13的MAX_STREAMS帧应用于单向流。

MAX_STREAMS帧如下:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     最大流(Maximum Streams) (i)                     ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

MAX_STREAMS帧包含以下字段:

最大流(Maximum Streams):

: 在连接的生存期内可以打开的相应类型的流的累计数量的计数。

丢失或重新排序可能导致接收声明流限制低于终端之前接收到的流限制MAX_STREAMS帧。
不增加流限制的MAX_STREAMS帧**必须**被忽略。

终端打开的流**不能**超过其对端设置的当前流限制。
例如，接收单向流限制为3的服务器可以打开流3、7和11，但不能打开流15。
如果对端打开多于允许的流数，终端**必须**使用STREAM_LIMIT_ERROR错误终止连接。

注意，这些帧(以及相应的传输参数)并不描述可以并发打开的流的数量。
这流数的限制包括已关闭的流和已打开的流。

## DATA_BLOCKED帧(DATA_BLOCKED Frame) {#frame-data-blocked}

当发送方希望发送数据但由于连接级流控制而无法发送数据时(参见{{flow-control}})，
它**应该**发送DATA_BLOCKED帧(类型=0x14)。
DATA_BLOCKED帧可以用作流控制算法调优的输入(参见{{fc-credit}})。

DATA_BLOCKED帧如下:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       数据限制(Data Limit) (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

DATA_BLOCKED帧包含以下字段:

数据限制(Data Limit):

: 一个可变长度整数，指示发生阻塞时的连接级别限制。

## 流数据阻塞帧(STREAM_DATA_BLOCKED Frame) {#frame-stream-data-blocked}

发送者当希望发送数据但是因为流级别的流量控制不能发送的时候**应该**发送一个STREAM_DATA_BLOCKED帧(类型是0x15)。
这个帧是和DATA_BLOCKED({{frame-data-blocked}})类似的。

对于一个仅发送的流，接受到STREAM_DATA_BLOCKED帧的终端**必须**以STREAM_STATE_ERROR的异常中断连接。

STREAM_DATA_BLOCKED帧结构如下:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Stream ID (i)                        ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Stream Data Limit (i)                    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

STREAM_DATA_BLOCKED帧包含以下字段:

流ID(Stream ID):

: 一个变长整数，标识被流控阻塞的流。

流数据限额(Stream Data Limit):

: 一个变长的整数，标识流阻塞出现的偏移量。


## 流阻塞帧(STREAMS_BLOCKED Frames) {#frame-streams-blocked}

当希望打开一个流，但是因为对端设置的最大流上限(详见{{frame-max-streams}})无法打开的时候，
发送者**应该**发送一个STREAMS_BLOCKED帧(类型0x16或者0x17)。
类型0x16的STREAMS_BLOCKED帧用于表示到达了双向流上限，类型0x17的STREAMS_BLOCKED帧用于表示到达了单向流上限。


STREAMS_BLOCKED帧不打开流，但是告知对端需要一个新的流并且流控制阻止了流的创建。

STREAMS_BLOCKED帧的结构如下:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Stream Limit (i)                     ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

STREAMS_BLOCKED帧包含以下字段:

流上限(Stream Limit):

: 一个变长整数，表示帧发送时的流上限。


## 新连接ID帧(NEW_CONNECTION_ID Frame) {#frame-new-connection-id}

终端发送NEW_CONNECTION_ID帧(类型0x18)来给对端提供
可用于当连接迁移的时候中断可连接性(详见{{migration-linkability}})的代替连接ID。

NEW_CONNECTION_ID 帧结构如下:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Sequence Number (i)                    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Length (8)  |                                               |
+-+-+-+-+-+-+-+-+       Connection ID (32..144)                 +
|                                                             ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                                                               +
|                                                               |
+                   Stateless Reset Token (128)                 +
|                                                               |
+                                                               +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

NEW_CONNECTION_ID 帧包含以下字段:

序列号(Sequence Number):

: 由发送者复制给连接ID的序列号。详见{{issue-cid}}。

长度(Length):

: 一个八位无符号的整数，包含连接ID的长度。小于4和大于18的值都是无效的而且**必须**以PROTOCOL_VIOLATION类型连接异常来处理。

连接ID(Connection ID):

: 指定长度的连接ID。

无状态重置凭证(Stateless Reset Token):

: 一个128位的值，用于关联的连接ID被使用时的无状态连接重置(详见{{stateless-reset}})。

如果它现在需要对端使用0长度的目标连接ID发送包，终端**禁止**发送这个帧。
从0长度或到0长度的对连接ID的长度的改变将会使得很难辨别何时连接ID的值发生了改变。
以0长度目的连接ID发送包的终端**必须**以PROTOCOL_VIOLATION类型的连接异常处理接收到的NEW_CONNECTION_ID帧。

传输异常，超时和重传可能导致相同的NEW_CONNECTION_ID帧被收到多次。
多次相同NEW_CONNECTION_ID帧的接收**禁止**被处理为连接异常。
接收者可以使用提供在NEW_CONNECTION_ID帧中的序列号来辨别新旧链接ID。

如果终端接收到了一个与之前发出的链接ID拥有不同的无状态重置凭证或不同序列号或者序列号用于其他连接ID的NEW_CONNECTION_ID帧，
终端**可以**以PROTOCOL_VIOLATION类型的连接异常来处理。


## 销毁连接ID帧(RETIRE_CONNECTION_ID Frame) {#frame-retire-connection-id}

终端发送RETIRE_CONNECTION_ID帧(类型0x19)来表示它将不再会使用对端发出的连接ID。
这可能包括握手期间提供的连接ID。
发送RETIRE_CONNECTION_ID帧也用于请求对端发送额外的连接ID供未来使用(详见 {{connection-id}})。
新连接ID可以用NEW_CONNECTION_ID帧来发送到对端。({{frame-new-connection-id}})

销毁连接ID也无效化了关联这个连接ID的无状态重置凭证。

RETIRE_CONNECTION_ID帧结构如下:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Sequence Number (i)                    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

RETIRE_CONNECTION_ID 帧包含以下字段:

序列号(Sequence Number):

: 将要销毁的连接ID的序列号。详见{{retiring-cids}}.

终端接收到包含大于任何之前发送到对端的序列号的 RETIRE_CONNECTION_ID
帧**可以**以PROTOCOL_VIOLATION类型的连接异常来处理。

在 RETIRE_CONNECTION_ID 帧中指定的序列号**禁止**引用包含此帧的包的目标连接ID字段。
对端**可以**以PROTOCOL_VIOLATION类型的连接异常来处理。

如果对端已经提供过了0长度的连接ID，终端不能发送此帧。
提供0长度的连接ID的终端若收到RETIRE_CONNECTION_ID帧，**必须**以PROTOCOL_VIOLATION类型的连接异常来处理。


## PATH_CHALLENGE帧(PATH_CHALLENGE Frame) {#frame-path-challenge}

端点可以使用PATH_CHALLENGE帧(类型=0x1a)来检查
到对端的可达性以及连接迁移期间的路径验证。

PATH_CHALLENGE帧如下所示:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                           数据 (64)                           +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

PATH_CHALLENGE帧包含如下字段:

数字:

: 这个8字节的字段包含任意数据。

包含难以猜测的8个字节的PATH_CHALLENGE帧足以
确保接收数据包比正确猜测该值更容易。

此帧的收件人**必须**生成包含相同数据的PATH_RESSION帧
({{frame-path-response}})。


## PATH_RESPONSE帧 (PATH_RESPONSE Frame) {#frame-path-response}

PATH_RESPONSE帧（type=0x1B）作为PATH_CHALLENGE帧
的响应发送。其格式与PATH_CHALLENGE帧({{frame-path-challenge}})
相同。

如果PATH_RESPONSE帧的内容与先前由端点发送的PATH_CHALLENGE帧
的内容不匹配，则端点**可能**会生成PROTOCOL_VIOLATION类型
的连接错误。

## CONNECTION_CLOSE 帧 (CONNECTION_CLOSE Frames) {#frame-connection-close}

端点发送CONNECTION_CLOSE帧(type=0x1c或0x1d)通知其对端
连接正在关闭。帧类型为0x1c的CONNECTION_CLOSE帧仅用于在
QUIC层发出错误信号，或表示没有错误(带有NO_ERROR码)。
类型为0x1d的CONNECTION_CLOSE帧用于向使用QUIC的应用
发出错误信号。

如果有未显式关闭的开放流，则当连接关闭时，它们将隐式关闭。

CONNECTION_CLOSE帧如下所示:

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           错误码 (16)     |          [ 帧类型 (i) ]     ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    原因短语长度 (i)                 ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        原因短语 (*)                    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~

CONNECTION_CLOSE帧包含以下字段:

错误码:

: 指示关闭此连接的原因的16位错误代码。类型为0x1c的
  CONNECTION_CLOSE帧使用{{error-codes}}中定义的
  空间中的代码。类型为0x1d的CONNECTION_CLOSE帧使
  用来自应用协议错误码空间的代码，请参见{{app-error-codes}}

帧类型:

: 一个可变长度整数，用于编码触发错误的帧的类型。
  当帧类型未知时，使用值0（相当于提到PADDING帧）。
  CONNECTION_CLOSE的应用特定变体(类型0x1d)不
  包括此字段。

原因短语长度:

: 以字节为单位指定原因短语的长度的可变长度整数。
  由于连接关闭帧不能在数据包之间拆分，因此对数据
  包大小的任何限制也会限制原因短语的可用空间。

原因短语:

: 对连接关闭原因的人类可读的解释。
  如果发送方选择不提供错误代码以外的详细信息，
  则长度可以为零。这应该是UTF-8编码的字符串 {{!RFC3629}}。


## 扩展帧(Extension Frames)

QUIC帧不使用自描述编码。因此，端点需要了解所有帧的语法，
才能成功处理数据包。这允许对帧进行有效的编码，但这意味着
端点不能发送对端未知类型的帧。

如果QUIC的扩展希望使用新类型的帧，则**必须**首先确保对端能够
理解该帧。端点可以使用传输参数来表示它愿意接收带有一个传输
参数的一个或多个扩展帧类型。

扩展帧必须是拥塞控制的，并且必须发送ACK帧。替换或补充ACK帧的
扩展帧除外。除非在扩展中指定，否则扩展帧不包括在流量控制中。

IANA注册表用于管理帧类型的分配，请参见{{iana-frames}}。

# 传输错误码（Transport Error Codes） {#error-codes}

QUIC错误码都是16位的无符号整型数。

本节列出了可能在CONNECTION_CLOSE帧中
使用的QUIC错误码的定义。这些错误可能在
整个连接过程中发生。

NO_ERROR (0x0):

: 终端通过使用携带这个错误码的CONNECTION_CLOSE帧
来表明连接在没有发生任何错误的情况下突然关闭。

INTERNAL_ERROR (0x1):

: 终端遇到内部错误无法继续维持连接。

SERVER_BUSY (0x2):

: 服务器当前繁忙且不会接受任何新的连接。

FLOW_CONTROL_ERROR (0x3):

: 终端收到的数据超过其通知的数据限制所允许的数量。
(请参见{{flow-control}})。

STREAM_LIMIT_ERROR (0x4):

: 终端接收到超出了其通知的流类型限制的帧。

STREAM_STATE_ERROR (0x5):

: 终端在允许接收该帧的状态之外的
状态接收到该帧(请参见{{stream-states}})。

FINAL_SIZE_ERROR (0x6):

: 终端收到的STREAM帧包含的数据
超过了先前确定的最终大小。
或者，终端接收的STREAM帧或RESET_STREAM帧的
最终大小于已接收的流数据的大小。
或者，终端接收的STREAM帧或RESET_STREAM帧
中包含与已建立的最终大小值不同。

FRAME_ENCODING_ERROR (0x7):

: 终端收到格式错误的帧。
例如，未知类型的帧，
或者确认范围大于包其余部分的ACK帧。


TRANSPORT_PARAMETER_ERROR (0x8):

: 终端接收的传输参数格式错误、包含无效值、
是必填的但不存在、
出现了不允许的值，或在其他情况下出错。

PROTOCOL_VIOLATION (0xA):

: 终端检测到的错误在协议范围内
没有更具体的错误代码。

INVALID_MIGRATION (0xC):

: 在终端禁用了迁移的状态下，
对端迁移到其他网络。

CRYPTO_ERROR (0x1XX):

: 加密握手失败。
保留256个值的范围用于传送特定于
所使用的加密握手的错误代码。
在{{QUIC-TLS}}的第4.8节中介绍了
将TLS用于加密握手时会出现的错误码。

有关新错误码的详细信息，请参阅{{iana-error-codes}}。


## 应用协议错误码（Application Protocol Error Codes） {#app-error-codes}

应用协议的错误码是16位无符号整数，但应用错误码的
管理由应用协议负责。
应用协议错误码用于RESET_STREAM帧
({{frame-reset-stream}})和
类型为0x1d({{frame-connection-close}})的
CONNECTION_CLOSE帧。


# 安全注意事项（Security Considerations）

## 握手拒绝服务（Handshake Denial of Service）

作为一种经过加密和验证的传输，
QUIC提供了一系列针对拒绝服务的保护。
一旦加密握手完成后，QUIC终端将丢弃大多数
未经身份验证的包，从而极大地限制了
攻击者干扰现有连接的能力。

一旦建立了连接，QUIC终端可能会接受一些
未经身份验证的ICMP包(请参阅{{icmp-pmtud}})，
但这些包的使用受到极大限制。
终端可能接受的唯一其他类型的包是
无状态重置({{stateless-reset}})，
该重置依赖于在使用前一直保密的令牌。

在创建连接期间，QUIC提供的保护仅针对
来自网络路径之外的攻击。
所有QUIC包都包含接收方收到来自其
对端的前面的包的证明。

防御使用的第一种机制是源连接ID和目标连接ID，
这是匹配对端所设置的连接ID所必需的。
除了初始和无状态重置数据包外，
终端仅接受包含与终端先前选择的连接ID
所匹配的目标连接的包。
这是为版本协商包提供的唯一保护。

初始包中客户端选择的目标连接ID值
不可预测是为另一个目的提供服务。
携带密码握手的包受来自该连接ID和
特定于QUIC协议版本的盐派生的密钥来保护。
这允许终端在完成加密握手后使用和自身使用的
相同的流程来验证它们收到的包。
无法验证的包会被丢弃。
以这种方式保护包提供了一个强有力的保证，
即该包的发送方收到初始包并正确理解它。

这些保护措施并不是为了有效对抗能够
在建立连接之前接收到多个包的攻击者，。
这样的攻击者可能会发送能被QUIC终端接受的包。
本版本的QUIC协议试图检测这种攻击，
但是它期望终端不会建立连接而不是恢复连接。
大多数情况下，加密握手协议{{QUIC-TLS}}负责
检测握手期间的篡改。

终端允许使用其他方法来检测和尝试
从握手受到的干扰中恢复。
无效包可以使用其他方法来标识和丢弃，
但本文档中没有指定特定方法。

## 重放攻击(Amplification Attack)

攻击者可能能够从服务器
接收地址验证令牌({{address-validation}}),
然后解码其中获取该令牌的IP地址。
稍后，
攻击者可以通过伪造该地址来启动与服务器的0-RTT连接，
此时该地址实际指向一个（被攻击的目标）终端。
为此，
攻击者可能会使服务器向目标发送初始拥塞窗口的数据。

服务器**应该**通过限制地址验证令牌的使用和生命周期
来缓解此种攻击（参见{{validate-future}}）。

## 乐观ACK攻击预期(Optimistic ACK Attack)

确认未收到数据包的终端可能
导致拥塞控制允许以超出网络支持的速率发送。
终端**可以**在发送数据包时跳过数据包编号以检测此行为。
若发现，终端可以立即以PROTOCOL_VIOLATION
类型错误立刻关闭连接（请参阅{{immediate-close}}。


## Slowloris攻击(Slowloris Attacks)

Slowloris {{SLOWLORIS}}攻击尝试保持与目标终端的
多个连接打开并维持尽可能长的时间。
针对某个 QUIC 终端执行这种攻击，
可以通过执行能避免因不活动而关闭
所需的最低数量的动作来进行。
这可能涉及发送少量数据，
逐步打开流控制窗口以控制发送速率，
或制造模拟高丢失率的ACK帧。

QUIC部署**应该**为Slowloris攻击提供缓解机制:
例如增加服务器允许的最大客户端数量，
限制允许单个IP地址进行的连接数量，
对允许连接的最小传输速度施加限制，
限制允许终端保持连接的时间长度等。


## 流碎片和重组攻击(Stream Fragmentation and Reassembly Attacks)

敌对发送者可能故意发送流数据的片段，
以便导致不成比例的接收缓冲内存耗费
和/或创建大而低效的数据结构。

一个敌对接收者可能故意不确认包含流数据的分组，
迫使发送者存储未确认的流数据以进行重传。

如果流控制窗口对应了可用内存，
则可减轻对接收者的攻击。
但是，某些接收者会过量使用内存并建议了总计
超过实际可用内存的控制器偏移量(即内存溢出至声明外)。
当终端表现良好时，过度耗费策略可以带来更好的性能，
但是使终端容易受到流碎片攻击。

QUIC部署**应该**提供缓解流碎片攻击的措施。
缓解措施可以包括避免过度耗费内存，
限制跟踪数据结构的大小，延迟STREAM帧的重组，
基于重组孔的寿命和持续时间或某种组合实现的启发式。


## 流耗费攻击(Stream Commitment Attack)

敌对终端可以打开大量流，耗尽目标终端上的状态。
并且敌对终端可以在大量连接上重复该过程，
其方式类似于TCP中的SYN泛洪攻击。

通常，客户端将按顺序打开流，如{{stream-id}}中所述。
然而，当以短间隔启动若干流时，
传输错误可能导致STREAM DATA帧打开流不被接收。
如果接收到更高编号的流ID，则接收方有义务打开中间流。
因此，在新连接上，
打开流2000001时将按照规范的要求打开100万个流。

活动流的数量受并发流限制传输参数的限制，
如{{controlling-concurrency}}中所述。
如果明智地选择，这个限制可以减轻流承诺攻击的影响。
但是，当应用程序期望打开大量流时，
将限制设置得太低可能会影响性能。

## 显式拥塞通知攻击(Explicit Congestion Notification Attacks) {#security-ecn}

路径上的攻击者可以操纵IP头中的
ECN码点的值来影响发送者的速率。
{{!RFC3168}} 更详细地讨论了操作及其影响。

端到端的攻击者可以复制并发送
带有修改的ECN码点的数据包，
以影响发送者的速率。
如果接收方丢弃重复的数据包，
则路径外攻击者需要将重复的数据包
与原始数据包竞争才能在此攻击中成功。
因此，QUIC接收者会忽略在重复数据包中
设置的ECN码点（请参阅{{ecn}}）。

## 无状态重置Oracle(Stateless Reset Oracle) {#reset-oracle}

无状态重置可能会产生类似于TCP重置注入的拒绝服务攻击。
如果攻击者能够为具有所选连接ID的
连接生成无状态重置令牌，
则就有可能发起此攻击。
能生成此令牌的攻击者可以使用相同的连接ID重置活动连接。

如果数据包可以路由到共享静态密钥的不同实例
（例如，通过更改IP地址或端口），
则攻击者可以使服务器发送无状态重置。
为了抵御这种拒绝服务攻击，
**必须**安排共享静态密钥以进行无状态重置的终端
（请参阅{{reset-token}}），
以便具有给定连接ID的数据包始终到达具有连接状态的实例，
除非该连接不再活动。

对于使用动态负载平衡的集群，
当活动实例保留连接状态时，
可能会发生负载均衡器配置的更改;
即使实例保留连接状态，
路由更改和结果无状态重置也会导致连接终止。
如果数据包无法路由到正确的实例，
则最好发送无状态重置，而不是等待连接超时。
但是，这只有在路由不受攻击者
影响的情况下才是可接受的。

## 版本降级(Version Downgrade) {#version-downgrade}

本文档定义了QUIC版本协商数据包{{version-negotiation}}，
可用于协商两个终端之间使用的QUIC版本。
但是，本文档未指定在此版本与
后续版本之间如何执行此协商。
特别的是，
版本协商数据包不包含任何防止版本降级攻击的机制。
使用版本协商数据包的QUIC的未来版本
**必须**定义一种对版本降级攻击具有强大功能的机制。


# IANA注意事项(IANA Considerations)

## QUIC传输参数注册信息(QUIC Transport Parameter Registry) {#iana-transport-parameters}

IANA \[SHALL add/has added] a registry for "QUIC Transport Parameters" under a
"QUIC Protocol" heading.

“QUIC传输参数”注册信息管理了一个16位空间。
此空间分为两个子空间，由不同的策略管理。
具有0x00到0xfe（十六进制）范围内的第一个字节
的值通过规范必需策略{{!RFC8126}}分配。
第一个字节0xff的值保留给私有信息，参考{{!RFC8126}}。

注册**必须**包括以下字段：

值:

: 分配的数值 (范围在0x0000~0xfeff).

参数名:

: 参数的缩写名称。

格式:

: 值的公开可用规范的参考。

指定专家验证规范是否存在且易于访问。
鼓励专家偏向批准注册，除非他们是滥用，
草率或有意产生危害的（不能仅仅是
美学上令人不悦，或在架构上存疑的）。

此注册信息的初始内容显示在{{iana-tp-table}}中。

| Value  | Parameter Name              | Specification                       |
|:-------|:----------------------------|:------------------------------------|
| 0x0000 | original_connection_id      | {{transport-parameter-definitions}} |
| 0x0001 | idle_timeout                | {{transport-parameter-definitions}} |
| 0x0002 | stateless_reset_token       | {{transport-parameter-definitions}} |
| 0x0003 | max_packet_size             | {{transport-parameter-definitions}} |
| 0x0004 | initial_max_data            | {{transport-parameter-definitions}} |
| 0x0005 | initial_max_stream_data_bidi_local | {{transport-parameter-definitions}} |
| 0x0006 | initial_max_stream_data_bidi_remote | {{transport-parameter-definitions}} |
| 0x0007 | initial_max_stream_data_uni | {{transport-parameter-definitions}} |
| 0x0008 | initial_max_streams_bidi    | {{transport-parameter-definitions}} |
| 0x0009 | initial_max_streams_uni     | {{transport-parameter-definitions}} |
| 0x000a | ack_delay_exponent          | {{transport-parameter-definitions}} |
| 0x000b | max_ack_delay               | {{transport-parameter-definitions}} |
| 0x000c | disable_migration           | {{transport-parameter-definitions}} |
| 0x000d | preferred_address           | {{transport-parameter-definitions}} |
{: #iana-tp-table title="Initial QUIC Transport Parameters Entries"}

## QUIC 帧种类注册处(QUIC Frame Type Registry) {#iana-frames}

IANA \[**应当**增加/已增加]一个在"QUIC协议"打头的用于QUIC 帧种类的注册处。

QUIC 帧种类注册处管理着一个62位的空间。
这个空间划分为由不同策略管理的三块空间。
在0x00到0x3f(十六进制)之间的值通过标准行为或者IESG审核策略{{!RFC8126}}分配。
在0x40到0x3fff之间的值通过声明必须政策{{!RFC8126}}进行操作分配。
所有其他值由私有策略{{!RFC8126}}分配。

注册**必须**包含以下字段:

值:

: 数值类型的值(注册会在0x00到0x3fff之间)。这区间内的值可能会被赋予。

帧名字:

: 一个帧种类的简短词语。

说明:

: 一个引用到公开访问的关于这个值的说明。

提名专家校验说明存在而且便利易读。
对于新的注册的说明需要描述哪一边终端可能决定它可以发送指定种类的帧。
大部分注册都需要伴随着的传输参数注册(详见{{iana-transport-parameters}})。
说明需要描述帧中的所有字段的格式和语义。

鼓励专家偏向批准注册，除非他们是滥用，草率或有意产生危害的。（不能仅仅是美学上令人不悦，或在架构上存疑的）

注册处的初始内容列在{{frame-types}}中。


## QUIC 传输错误码注册处(QUIC Transport Error Codes Registry) {#iana-error-codes}

IANA \[**应当**增加/已增加]一个在"QUIC协议"打头的用于QUIC 传输错误码的注册处。

"QUIC 传输错误码"注册处管理着一个十六位的空间。
这个空间被分为由不同策略管理的两个空间。
在第一个字节在0x00到0xfe(十六进制)范围内的值通过声明必须策略 {{!RFC8126}}分配。
第一字节的值是0xff的值保留用于私有策略{{!RFC8126}}。

注册处**必须**包含以下字段:

值:

: 数值类型的值(注册会在0x0000到0xfeff之间)。

错误码:

: 一个表示参数的简短词语。

描述:

: 一个错误码语义的简短描述，如果提供了说明引用，**可能**是一个总结。

说明:

: 一个引用到公开访问的关于这个值的说明。

注册处的初始内容列在{{iana-error-table}}中。
在0xFF00 到 0xFFFF 之间的值保留用于私有{{!RFC8126}}。

| Value | Error                     | Description                   | Specification   |
|:------|:--------------------------|:------------------------------|:----------------|
| 0x0   | NO_ERROR                  | No error                      | {{error-codes}} |
| 0x1   | INTERNAL_ERROR            | Implementation error          | {{error-codes}} |
| 0x2   | SERVER_BUSY               | Server currently busy         | {{error-codes}} |
| 0x3   | FLOW_CONTROL_ERROR        | Flow control error            | {{error-codes}} |
| 0x4   | STREAM_LIMIT_ERROR        | Too many streams opened       | {{error-codes}} |
| 0x5   | STREAM_STATE_ERROR        | Frame received in invalid stream state | {{error-codes}} |
| 0x6   | FINAL_SIZE_ERROR          | Change to final size          | {{error-codes}} |
| 0x7   | FRAME_ENCODING_ERROR      | Frame encoding error          | {{error-codes}} |
| 0x8   | TRANSPORT_PARAMETER_ERROR | Error in transport parameters | {{error-codes}} |
| 0xA   | PROTOCOL_VIOLATION        | Generic protocol violation    | {{error-codes}} |
| 0xC   | INVALID_MIGRATION         | Violated disabled migration   | {{error-codes}} |
{: #iana-error-table title="初始QUIC 传输错误码条目(Initial QUIC Transport Error Codes Entries)"}


--- back

# Sample Packet Number Decoding Algorithm {#sample-packet-number-decoding}

The following pseudo-code shows how an implementation can decode packet
numbers after header protection has been removed.

~~~
DecodePacketNumber(largest_pn, truncated_pn, pn_nbits):
   expected_pn  = largest_pn + 1
   pn_win       = 1 << pn_nbits
   pn_hwin      = pn_win / 2
   pn_mask      = pn_win - 1
   // The incoming packet number should be greater than
   // expected_pn - pn_hwin and less than or equal to
   // expected_pn + pn_hwin
   //
   // This means we can't just strip the trailing bits from
   // expected_pn and add the truncated_pn because that might
   // yield a value outside the window.
   //
   // The following code calculates a candidate value and
   // makes sure it's within the packet number window.
   candidate_pn = (expected_pn & ~pn_mask) | truncated_pn
   if candidate_pn <= expected_pn - pn_hwin:
      return candidate_pn + pn_win
   // Note the extra check for underflow when candidate_pn
   // is near zero.
   if candidate_pn > expected_pn + pn_hwin and
      candidate_pn > pn_win:
      return candidate_pn - pn_win
   return candidate_pn
~~~

# Change Log

> **RFC Editor's Note:** Please remove this section prior to publication of a
> final version of this document.

Issue and pull request numbers are listed with a leading octothorp.

## Since draft-ietf-quic-transport-17

- Stream-related errors now use STREAM_STATE_ERROR (#2305)
- Endpoints discard initial keys as soon as handshake keys are available (#1951,
  #2045)
- Expanded conditions for ignoring ICMP packet too big messages (#2108, #2161)
- Remove rate control from PATH_CHALLENGE/PATH_RESPONSE (#2129, #2241)
- Endpoints are permitted to discard malformed initial packets (#2141)
- Clarified ECN implementation and usage requirements (#2156, #2201)
- Disable ECN count verification for packets that arrive out of order (#2198,
  #2215)
- Use Probe Timeout (PTO) instead of RTO (#2206, #2238)
- Loosen constraints on retransmission of ACK ranges (#2199, #2245)
- Limit Retry and Version Negotiation to once per datagram (#2259, #2303)
- Set a maximum value for max_ack_delay transport parameter (#2282, #2301)
- Allow server preferred address for both IPv4 and IPv6 (#2122, #2296)
- Corrected requirements for migration to a preferred address (#2146, #2349)
- ACK of non-existent packet is illegal (#2298, #2302)

## Since draft-ietf-quic-transport-16

- Stream limits are defined as counts, not maximums (#1850, #1906)
- Require amplification attack defense after closing (#1905, #1911)
- Remove reservation of application error code 0 for STOPPING (#1804, #1922)
- Renumbered frames (#1945)
- Renumbered transport parameters (#1946)
- Numeric transport parameters are expressed as varints (#1608, #1947, #1955)
- Reorder the NEW_CONNECTION_ID frame (#1952, #1963)
- Rework the first byte (#2006)
  - Fix the 0x40 bit
  - Change type values for long header
  - Add spin bit to short header (#631, #1988)
  - Encrypt the remainder of the first byte (#1322)
  - Move packet number length to first byte
  - Move ODCIL to first byte of retry packets
  - Simplify packet number protection (#1575)
- Allow STOP_SENDING to open a remote bidirectional stream (#1797, #2013)
- Added mitigation for off-path migration attacks (#1278, #1749, #2033)
- Don't let the PMTU to drop below 1280 (#2063, #2069)
- Require peers to replace retired connection IDs (#2085)
- Servers are required to ignore Version Negotiation packets (#2088)
- Tokens are repeated in all Initial packets (#2089)
- Clarified how PING frames are sent after loss (#2094)
- Initial keys are discarded once Handshake are available (#1951, #2045)
- ICMP PTB validation clarifications (#2161, #2109, #2108)


## Since draft-ietf-quic-transport-15

Substantial editorial reorganization; no technical changes.

## Since draft-ietf-quic-transport-14

- Merge ACK and ACK_ECN (#1778, #1801)
- Explicitly communicate max_ack_delay (#981, #1781)
- Validate original connection ID after Retry packets (#1710, #1486, #1793)
- Idle timeout is optional and has no specified maximum (#1765)
- Update connection ID handling; add RETIRE_CONNECTION_ID type (#1464, #1468,
  #1483, #1484, #1486, #1495, #1729, #1742, #1799, #1821)
- Include a Token in all Initial packets (#1649, #1794)
- Prevent handshake deadlock (#1764, #1824)

## Since draft-ietf-quic-transport-13

- Streams open when higher-numbered streams of the same type open (#1342, #1549)
- Split initial stream flow control limit into 3 transport parameters (#1016,
  #1542)
- All flow control transport parameters are optional (#1610)
- Removed UNSOLICITED_PATH_RESPONSE error code (#1265, #1539)
- Permit stateless reset in response to any packet (#1348, #1553)
- Recommended defense against stateless reset spoofing (#1386, #1554)
- Prevent infinite stateless reset exchanges (#1443, #1627)
- Forbid processing of the same packet number twice (#1405, #1624)
- Added a packet number decoding example (#1493)
- More precisely define idle timeout (#1429, #1614, #1652)
- Corrected format of Retry packet and prevented looping (#1492, #1451, #1448,
  #1498)
- Permit 0-RTT after receiving Version Negotiation or Retry (#1507, #1514,
  #1621)
- Permit Retry in response to 0-RTT (#1547, #1552)
- Looser verification of ECN counters to account for ACK loss (#1555, #1481,
  #1565)
- Remove frame type field from APPLICATION_CLOSE (#1508, #1528)


## Since draft-ietf-quic-transport-12

- Changes to integration of the TLS handshake (#829, #1018, #1094, #1165, #1190,
  #1233, #1242, #1252, #1450, #1458)
  - The cryptographic handshake uses CRYPTO frames, not stream 0
  - QUIC packet protection is used in place of TLS record protection
  - Separate QUIC packet number spaces are used for the handshake
  - Changed Retry to be independent of the cryptographic handshake
  - Added NEW_TOKEN frame and Token fields to Initial packet
  - Limit the use of HelloRetryRequest to address TLS needs (like key shares)
- Enable server to transition connections to a preferred address (#560, #1251,
  #1373)
- Added ECN feedback mechanisms and handling; new ACK_ECN frame (#804, #805,
  #1372)
- Changed rules and recommendations for use of new connection IDs (#1258, #1264,
  #1276, #1280, #1419, #1452, #1453, #1465)
- Added a transport parameter to disable intentional connection migration
  (#1271, #1447)
- Packets from different connection ID can't be coalesced (#1287, #1423)
- Fixed sampling method for packet number encryption; the length field in long
  headers includes the packet number field in addition to the packet payload
  (#1387, #1389)
- Stateless Reset is now symmetric and subject to size constraints (#466, #1346)
- Added frame type extension mechanism (#58, #1473)


## Since draft-ietf-quic-transport-11

- Enable server to transition connections to a preferred address (#560, #1251)
- Packet numbers are encrypted (#1174, #1043, #1048, #1034, #850, #990, #734,
  #1317, #1267, #1079)
- Packet numbers use a variable-length encoding (#989, #1334)
- STREAM frames can now be empty (#1350)

## Since draft-ietf-quic-transport-10

- Swap payload length and packed number fields in long header (#1294)
- Clarified that CONNECTION_CLOSE is allowed in Handshake packet (#1274)
- Spin bit reserved (#1283)
- Coalescing multiple QUIC packets in a UDP datagram (#1262, #1285)
- A more complete connection migration (#1249)
- Refine opportunistic ACK defense text (#305, #1030, #1185)
- A Stateless Reset Token isn't mandatory (#818, #1191)
- Removed implicit stream opening (#896, #1193)
- An empty STREAM frame can be used to open a stream without sending data (#901,
  #1194)
- Define stream counts in transport parameters rather than a maximum stream ID
  (#1023, #1065)
- STOP_SENDING is now prohibited before streams are used (#1050)
- Recommend including ACK in Retry packets and allow PADDING (#1067, #882)
- Endpoints now become closing after an idle timeout (#1178, #1179)
- Remove implication that Version Negotiation is sent when a packet of the wrong
  version is received (#1197)

## Since draft-ietf-quic-transport-09

- Added PATH_CHALLENGE and PATH_RESPONSE frames to replace PING with Data and
  PONG frame. Changed ACK frame type from 0x0e to 0x0d. (#1091, #725, #1086)
- A server can now only send 3 packets without validating the client address
  (#38, #1090)
- Delivery order of stream data is no longer strongly specified (#252, #1070)
- Rework of packet handling and version negotiation (#1038)
- Stream 0 is now exempt from flow control until the handshake completes (#1074,
  #725, #825, #1082)
- Improved retransmission rules for all frame types: information is
  retransmitted, not packets or frames (#463, #765, #1095, #1053)
- Added an error code for server busy signals (#1137)

- Endpoints now set the connection ID that their peer uses.  Connection IDs are
  variable length.  Removed the omit_connection_id transport parameter and the
  corresponding short header flag. (#1089, #1052, #1146, #821, #745, #821,
  #1166, #1151)

## Since draft-ietf-quic-transport-08

- Clarified requirements for BLOCKED usage (#65,  #924)
- BLOCKED frame now includes reason for blocking (#452, #924, #927, #928)
- GAP limitation in ACK Frame (#613)
- Improved PMTUD description (#614, #1036)
- Clarified stream state machine (#634, #662, #743, #894)
- Reserved versions don't need to be generated deterministically (#831, #931)
- You don't always need the draining period (#871)
- Stateless reset clarified as version-specific (#930, #986)
- initial_max_stream_id_x transport parameters are optional (#970, #971)
- Ack Delay assumes a default value during the handshake (#1007, #1009)
- Removed transport parameters from NewSessionTicket (#1015)

## Since draft-ietf-quic-transport-07

- The long header now has version before packet number (#926, #939)
- Rename and consolidate packet types (#846, #822, #847)
- Packet types are assigned new codepoints and the Connection ID Flag is
  inverted (#426, #956)
- Removed type for Version Negotiation and use Version 0 (#963, #968)
- Streams are split into unidirectional and bidirectional (#643, #656, #720,
  #872, #175, #885)
  * Stream limits now have separate uni- and bi-directional transport parameters
    (#909, #958)
  * Stream limit transport parameters are now optional and default to 0 (#970,
    #971)
- The stream state machine has been split into read and write (#634, #894)
- Employ variable-length integer encodings throughout (#595)
- Improvements to connection close
  * Added distinct closing and draining states (#899, #871)
  * Draining period can terminate early (#869, #870)
  * Clarifications about stateless reset (#889, #890)
- Address validation for connection migration (#161, #732, #878)
- Clearly defined retransmission rules for BLOCKED (#452, #65, #924)
- negotiated_version is sent in server transport parameters (#710, #959)
- Increased the range over which packet numbers are randomized (#864, #850,
  #964)

## Since draft-ietf-quic-transport-06

- Replaced FNV-1a with AES-GCM for all "Cleartext" packets (#554)
- Split error code space between application and transport (#485)
- Stateless reset token moved to end (#820)
- 1-RTT-protected long header types removed (#848)
- No acknowledgments during draining period (#852)
- Remove "application close" as a separate close type (#854)
- Remove timestamps from the ACK frame (#841)
- Require transport parameters to only appear once (#792)

## Since draft-ietf-quic-transport-05

- Stateless token is server-only (#726)
- Refactor section on connection termination (#733, #748, #328, #177)
- Limit size of Version Negotiation packet (#585)
- Clarify when and what to ack (#736)
- Renamed STREAM_ID_NEEDED to STREAM_ID_BLOCKED
- Clarify Keep-alive requirements (#729)

## Since draft-ietf-quic-transport-04

- Introduce STOP_SENDING frame, RESET_STREAM only resets in one direction (#165)
- Removed GOAWAY; application protocols are responsible for graceful shutdown
  (#696)
- Reduced the number of error codes (#96, #177, #184, #211)
- Version validation fields can't move or change (#121)
- Removed versions from the transport parameters in a NewSessionTicket message
  (#547)
- Clarify the meaning of "bytes in flight" (#550)
- Public reset is now stateless reset and not visible to the path (#215)
- Reordered bits and fields in STREAM frame (#620)
- Clarifications to the stream state machine (#572, #571)
- Increased the maximum length of the Largest Acknowledged field in ACK frames
  to 64 bits (#629)
- truncate_connection_id is renamed to omit_connection_id (#659)
- CONNECTION_CLOSE terminates the connection like TCP RST (#330, #328)
- Update labels used in HKDF-Expand-Label to match TLS 1.3 (#642)

## Since draft-ietf-quic-transport-03

- Change STREAM and RESET_STREAM layout
- Add MAX_STREAM_ID settings

## Since draft-ietf-quic-transport-02

- The size of the initial packet payload has a fixed minimum (#267, #472)
- Define when Version Negotiation packets are ignored (#284, #294, #241, #143,
  #474)
- The 64-bit FNV-1a algorithm is used for integrity protection of unprotected
  packets (#167, #480, #481, #517)
- Rework initial packet types to change how the connection ID is chosen (#482,
  #442, #493)
- No timestamps are forbidden in unprotected packets (#542, #429)
- Cryptographic handshake is now on stream 0 (#456)
- Remove congestion control exemption for cryptographic handshake (#248, #476)
- Version 1 of QUIC uses TLS; a new version is needed to use a different
  handshake protocol (#516)
- STREAM frames have a reduced number of offset lengths (#543, #430)
- Split some frames into separate connection- and stream- level frames
  (#443)
  - WINDOW_UPDATE split into MAX_DATA and MAX_STREAM_DATA (#450)
  - BLOCKED split to match WINDOW_UPDATE split (#454)
  - Define STREAM_ID_NEEDED frame (#455)
- A NEW_CONNECTION_ID frame supports connection migration without linkability
  (#232, #491, #496)
- Transport parameters for 0-RTT are retained from a previous connection (#405,
  #513, #512)
  - A client in 0-RTT no longer required to reset excess streams (#425, #479)
- Expanded security considerations (#440, #444, #445, #448)


## Since draft-ietf-quic-transport-01

- Defined short and long packet headers (#40, #148, #361)
- Defined a versioning scheme and stable fields (#51, #361)
- Define reserved version values for "greasing" negotiation (#112, #278)
- The initial packet number is randomized (#35, #283)
- Narrow the packet number encoding range requirement (#67, #286, #299, #323,
  #356)

- Defined client address validation (#52, #118, #120, #275)
- Define transport parameters as a TLS extension (#49, #122)
- SCUP and COPT parameters are no longer valid (#116, #117)
- Transport parameters for 0-RTT are either remembered from before, or assume
  default values (#126)
- The server chooses connection IDs in its final flight (#119, #349, #361)
- The server echoes the Connection ID and packet number fields when sending a
  Version Negotiation packet (#133, #295, #244)

- Defined a minimum packet size for the initial handshake packet from the client
  (#69, #136, #139, #164)
- Path MTU Discovery (#64, #106)
- The initial handshake packet from the client needs to fit in a single packet
  (#338)

- Forbid acknowledgment of packets containing only ACK and PADDING (#291)
- Require that frames are processed when packets are acknowledged (#381, #341)
- Removed the STOP_WAITING frame (#66)
- Don't require retransmission of old timestamps for lost ACK frames (#308)
- Clarified that frames are not retransmitted, but the information in them can
  be (#157, #298)

- Error handling definitions (#335)
- Split error codes into four sections (#74)
- Forbid the use of Public Reset where CONNECTION_CLOSE is possible (#289)

- Define packet protection rules (#336)

- Require that stream be entirely delivered or reset, including acknowledgment
  of all STREAM frames or the RESET_STREAM, before it closes (#381)
- Remove stream reservation from state machine (#174, #280)
- Only stream 1 does not contribute to connection-level flow control (#204)
- Stream 1 counts towards the maximum concurrent stream limit (#201, #282)
- Remove connection-level flow control exclusion for some streams (except 1)
  (#246)
- RESET_STREAM affects connection-level flow control (#162, #163)
- Flow control accounting uses the maximum data offset on each stream, rather
  than bytes received (#378)

- Moved length-determining fields to the start of STREAM and ACK (#168, #277)
- Added the ability to pad between frames (#158, #276)
- Remove error code and reason phrase from GOAWAY (#352, #355)
- GOAWAY includes a final stream number for both directions (#347)
- Error codes for RESET_STREAM and CONNECTION_CLOSE are now at a consistent
  offset (#249)

- Defined priority as the responsibility of the application protocol (#104,
  #303)


## Since draft-ietf-quic-transport-00

- Replaced DIVERSIFICATION_NONCE flag with KEY_PHASE flag
- Defined versioning
- Reworked description of packet and frame layout
- Error code space is divided into regions for each component
- Use big endian for all numeric values


## Since draft-hamilton-quic-transport-protocol-01

- Adopted as base for draft-ietf-quic-tls
- Updated authors/editors list
- Added IANA Considerations section
- Moved Contributors and Acknowledgments to appendices


# Acknowledgments
{:numbered="false"}

Special thanks are due to the following for helping shape pre-IETF QUIC and its
deployment: Chris Bentzel, Misha Efimov, Roberto Peon, Alistair Riddoch,
Siddharth Vijayakrishnan, and Assar Westerlund.

This document has benefited immensely from various private discussions and
public ones on the quic@ietf.org and proto-quic@chromium.org mailing lists. Our
thanks to all.


# Contributors
{:numbered="false"}

The original authors of this specification were Ryan Hamilton, Jana Iyengar, Ian
Swett, and Alyssa Wilk.

The original design and rationale behind this protocol draw significantly from
work by Jim Roskind {{EARLY-DESIGN}}. In alphabetical order, the contributors to
the pre-IETF QUIC project at Google are: Britt Cyr, Jeremy Dorfman, Ryan
Hamilton, Jana Iyengar, Fedor Kouranov, Charles Krasic, Jo Kulik, Adam Langley,
Jim Roskind, Robbie Shade, Satyam Shekhar, Cherie Shi, Ian Swett, Raman Tenneti,
Victor Vasiliev, Antonio Vicente, Patrik Westin, Alyssa Wilk, Dale Worley, Fan
Yang, Dan Zhang, Daniel Ziegler.
