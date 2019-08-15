---
title: Using TLS to Secure QUIC
abbrev: QUIC over TLS
docname: draft-ietf-quic-tls-latest
date: {DATE}
category: std
ipr: trust200902
area: Transport
workgroup: QUIC

stand_alone: yes
pi: [toc, sortrefs, symrefs, docmapping]

author:
  -
    ins: M. Thomson
    name: Martin Thomson
    org: Mozilla
    email: mt@lowentropy.net
    role: editor
  -
    ins: S. Turner
    name: Sean Turner
    org: sn3rd
    email: sean@sn3rd.com
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

informative:

  AEBounds:
    title: "Limits on Authenticated Encryption Use in TLS"
    author:
      - ins: A. Luykx
      - ins: K. Paterson
    date: 2016-03-08
    target: "http://www.isg.rhul.ac.uk/~kp/TLS-AEbounds.pdf"

  IMC:
    title: "Introduction to Modern Cryptography, Second Edition"
    author:
      - ins: J. Katz
      - ins: Y. Lindell
    date: 2014-11-06
    seriesinfo:
      ISBN: 978-1466570269

  QUIC-HTTP:
    title: "Hypertext Transfer Protocol (HTTP) over QUIC"
    date: {DATE}
    seriesinfo:
      Internet-Draft: draft-ietf-quic-http-latest
    author:
      -
        ins: M. Bishop
        name: Mike Bishop
        org: Microsoft
        role: editor


--- abstract

This document describes how Transport Layer Security (TLS) is used to secure
QUIC.

--- note_Note_to_Readers

Discussion of this draft takes place on the QUIC working group mailing list
(quic@ietf.org), which is archived at
<https://mailarchive.ietf.org/arch/search/?email_list=quic>.

Working Group information can be found at <https://github.com/quicwg>; source
code and issues list for this draft can be found at
<https://github.com/quicwg/base-drafts/labels/-tls>.

--- middle

# Introduction

This document describes how QUIC {{QUIC-TRANSPORT}} is secured using TLS
{{!TLS13=RFC8446}}.

TLS 1.3 provides critical latency improvements for connection establishment over
previous versions.  Absent packet loss, most new connections can be established
and secured within a single round trip; on subsequent connections between the
same client and server, the client can often send application data immediately,
that is, using a zero round trip setup.

This document describes how TLS acts as a security component of QUIC.


# Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in BCP 14 {{!RFC2119}} {{!RFC8174}}
when, and only when, they appear in all capitals, as shown here.

This document uses the terminology established in {{QUIC-TRANSPORT}}.

For brevity, the acronym TLS is used to refer to TLS 1.3, though a newer version
could be used (see {{tls-version}}).


## TLS Overview

TLS provides two endpoints with a way to establish a means of communication over
an untrusted medium (that is, the Internet) that ensures that messages they
exchange cannot be observed, modified, or forged.

Internally, TLS is a layered protocol, with the structure shown below:

~~~~
+--------------+--------------+--------------+
|  Handshake   |    Alerts    |  Application |
|    Layer     |              |     Data     |
|              |              |              |
+--------------+--------------+--------------+
|                                            |
|               Record Layer                 |
|                                            |
+--------------------------------------------+
~~~~

Each upper layer (handshake, alerts, and application data) is carried as a
series of typed TLS records. Records are individually cryptographically
protected and then transmitted over a reliable transport (typically TCP) which
provides sequencing and guaranteed delivery.

Change Cipher Spec records cannot be sent in QUIC.

The TLS authenticated key exchange occurs between two entities: client and
server.  The client initiates the exchange and the server responds.  If the key
exchange completes successfully, both client and server will agree on a secret.
TLS supports both pre-shared key (PSK) and Diffie-Hellman (DH) key exchanges.
PSK is the basis for 0-RTT; the latter provides perfect forward secrecy (PFS)
when the DH keys are destroyed.

After completing the TLS handshake, the client will have learned and
authenticated an identity for the server and the server is optionally able to
learn and authenticate an identity for the client.  TLS supports X.509
{{?RFC5280}} certificate-based authentication for both server and client.

The TLS key exchange is resistant to tampering by attackers and it produces
shared secrets that cannot be controlled by either participating peer.

TLS provides two basic handshake modes of interest to QUIC:

 * A full 1-RTT handshake in which the client is able to send application data
   after one round trip and the server immediately responds after receiving the
   first handshake message from the client.

 * A 0-RTT handshake in which the client uses information it has previously
   learned about the server to send application data immediately.  This
   application data can be replayed by an attacker so it MUST NOT carry a
   self-contained trigger for any non-idempotent action.

A simplified TLS handshake with 0-RTT application data is shown in {{tls-full}}.
Note that this omits the EndOfEarlyData message, which is not used in QUIC (see
{{remove-eoed}}).

~~~
    Client                                             Server

    ClientHello
   (0-RTT Application Data)  -------->
                                                  ServerHello
                                         {EncryptedExtensions}
                                                    {Finished}
                             <--------      [Application Data]
   {Finished}                -------->

   [Application Data]        <------->      [Application Data]

    () Indicates messages protected by early data (0-RTT) keys
    {} Indicates messages protected using handshake keys
    [] Indicates messages protected using application data
       (1-RTT) keys
~~~
{: #tls-full title="TLS Handshake with 0-RTT"}

Data is protected using a number of encryption levels:

- Initial Keys
- Early Data (0-RTT) Keys
- Handshake Keys
- Application Data (1-RTT) Keys

Application data may appear only in the early data and application data
levels. Handshake and Alert messages may appear in any level.

The 0-RTT handshake is only possible if the client and server have previously
communicated.  In the 1-RTT handshake, the client is unable to send protected
application data until it has received all of the handshake messages sent by the
server.


# 协议概述

QUIC {{QUIC-TRANSPORT}}负责保护数据包的机密性和完整性。为此，它使用从
TLS握手{{!TLS13}}派生的密钥，而不是通过QUIC(如TCP)携带TLS记录。TLS握手
和警报消息直接通过QUIC传输，相当于接管了TLS记录层的职责，如下所示。

~~~~

+--------------+--------------+ +-------------+
|     TLS      |     TLS      | |    QUIC     |
|     握手     |     警报      | | 应用        |
|              |              | |  (h3等)     |
+--------------+--------------+-+-------------+
|                                             |
|                QUIC 传输                    |
|              (流、可靠性、拥塞等)             |
|                                             |
+---------------------------------------------+
|                                             |
|           QUIC数据包保护                     |
|                                             |
+---------------------------------------------+
~~~~


QUIC还依赖TLS进行身份验证和参数协商，这些参数对安全性和性能至关重要。

这两个协议不是严格的分层，而是相互依赖的：QUIC使用TLS握手；TLS使用QUIC
提供的可靠性、有序交付和记录层。

在高层次上，TLS和QUIC组件之间有两种主要的交互作用：

* TLS组件通过QUIC组件发送和接收消息，QUIC为TLS提供可靠的流抽象。

* TLS组件向QUIC组件提供一系列更新，包括(a)用于安装的新的数据包保护密钥
  (b)状态更改，例如握手完成、服务器证书等。

{{schematic}}更详细地展示了这些交互，特别调用了QUIC数据包保护。

~~~
+------------+                        +------------+
|            |<-      握手消息      ->|            |
|            |<---- 0-RTT 密钥 -------|            |
|            |<--- 握手密钥-----|            |
|   QUIC     |<---- 1-RTT 密钥 -------|    TLS     |
|            |<--- 握手完成 ----|            |
+------------+                        +------------+
 |         ^
 | Protect | 受保护的包
 v         |
+------------+
|   QUIC     |
|  包保护 |
+------------+
~~~
{: #schematic title="QUIC和TLS交互"}

与TCP上的TLS不同，想要发送数据的QUIC应用程序不会通过TLS“application_data”
记录发送数据。相反，他们将其作为QUIC数据包中QUIC STREAM帧发送。

# 携带TLS消息 {#carrying-tls}

QUIC在CRYPTO帧中携带TLS握手数据，每个帧由偏移量和长度标识的连续握手数据块组成。
这些帧被打包成QUIC数据包，并在当前的TLS加密级别下进行加密。与TCP上的TLS一样，
一旦TLS握手数据传送到QUIC，QUIC就有责任可靠地传送它。TLS产生的每个数据块都与
TLS当前使用的一组密钥相关联。如果QUIC需要重新传输该数据，它**必须**使用相同的密钥，
即使TLS已经更新到更新的密钥。

TLS记录(与TCP一起使用)和QUIC加密帧之间的一个重要区别是，在QUIC中，多个帧可能
出现在同一个QUIC数据包中，只要它们与相同的加密级别相关联。例如，一个实现可以将
握手消息和一些握手数据的ACK捆绑到同一个包中。

每个加密级别具有可能出现在其中的帧的特定列表。这里的规则概括了TLS的规则，因为与
建立连接相关联的帧通常可以出现在任何加密级别，而与传输数据相关联的帧只能出现在
0-RTT和1-RTT加密级别中：

- CRYPTO帧**可以**出现在除0-RTT之外的任何加密级别的包中。

- CONNECTION_CLOSE帧**可以**可以出现在0-RTT以外的任何加密级别的数据包中。

- PADDING帧**可以**出现在任何加密级别的包中。

- ACK帧**可以**出现在除0-RTT之外的任何加密级别的包中，但只能确认出现在该包
  编号空间中的包。

- STREAM帧**只能**出现在0-RTT和1-RTT级别中。

- 所有其他帧类型**必须**出现在1-RTT级别。

因为数据包可以在线路上重新排序，所以QUIC使用数据包类型来指示在哪个级别下对给定
的数据包进行加密，如{{packet-types-levels}}所示。当需要发送多个不同加密级别的
数据包时，端点**应该**使用合并的数据包在同一UDP数据报中发送它们。

| 包类型     | 加密级别| PN 空间  |
|:----------------|:-----------------|:----------|
| 初始化         |初始密钥  |初始化   |
|0-RTT保护 | 0-RTT            | 0/1-RTT   |
| 握手       | 握手       | 握手 |
| 重试           | N/A              | N/A       |
| 短头部    | 1-RTT            | 0/1-RTT   |
{: #packet-types-levels title="按数据包类型划分的加密级别"}

{{QUIC-TRANSPORT}}的第17节展示了不同加密级别的数据包如何适合握手过程。

## 到TLS的接口

如{{schematic}}所示，QUIC到TLS的接口由三个主要函数组成：

- 发送和接收握手消息
- 更新密钥(发送和接收)
- 握手状态更新

配置TLS可能需要其他功能。


### 发送和接收握手信息

为了实现握手，TLS依赖于能够发送和接收握手消息。
这个接口有两个基本功能：
一个用于QUIC接收握手消息，
另一个用于QUIC提供握手数据包。

在开始握手之前，QUIC向TLS提供QUIC希望携带的传输参数(参见{{quic_parameters}})。

QUIC客户端通过从TLS请求TLS握手字节来启动TLS。
客户端在发送其第一个数据包之前获取握手字节。
QUIC服务器通过向TLS提供客户端的握手字节来启动进程。

在任何给定的时间，各终端处的TLS堆栈
将具有当前发送加密级别和接收加密级别信息。
每个加密级别信息与不同的字节流相关联，
字节流以CRYPTO帧的形式可靠地传输到对端。
当TLS提供要发送的握手字节时，
它们被附加到当前流中，
并且使用来自相应加密级别的密钥来
保护包括CRYPTO帧的任何分组。

QUIC将TLS握手记录中未受保护的内容
作为CRYPTO帧的内容。
QUIC不使用TLS记录保护。
QUIC将CRYPTO帧组装成QUIC数据包，
这些数据包使用QUIC数据包保护进行保护。

When an endpoint receives a QUIC packet containing a CRYPTO frame from the
network, it proceeds as follows:
当终端从网络接收到包含CRYPTO帧的
QUIC数据包时，它将按如下方式进行：

- 如果数据包的加密级别在TLS接收加密级别之内，
  则像往常一样将数据排序到输入流中。
  与STREAM帧一样，偏移用于在数据序列中找到正确的位置。
  如果此过程的结果是新数据可用，则按顺序将其交付给TLS。

- 如果数据包来自以前设置的加密级别，
  则它**禁止**包含超出该流中先前接收到的数据结尾的数据。
  协议实现**必须**将任何违反此要求
  的行为视为PROTOCOL_VIOLATION类型的连接错误。

- 如果数据包来自新的加密级别，则将其保存以供TLS稍后处理。
  一旦TLS移动到从这个加密级别接收，就可以提供保存的数据。
  将任何新加密级别的数据提供给TLS时，
  如果存在TLS尚未使用的以前加密级别的数据，
  则必须将其视为PROTOCOL_IVERSION类型的连接错误

每次向TLS提供新数据时，都会从TLS请求新的握手字节。
如果TLS接收到的握手消息不完整或没有数据要发送，
则TLS可能不提供任何字节。

一旦TLS握手完成，
这就是说QUIC收到了TLS需要发送的
任何最终握手字节C。
TLS还向QUIC提供对端在
握手期间通告的传输参数。

一旦握手完成，TLS就变成被动的。
TLS仍然可以从其对端接收数据并进行响应，
但它将不需要发送更多的数据，
除非有特别的请求-无论是由应用程序还是QUIC。
发送数据的一个原因是服务器
可能希望向客户端提供额外的或更新的会话凭证。

握手完成后，QUIC只需向TLS提供
任何以加密流形式到达的数据。
以与握手期间所做的相同的方式，
在提供接收到的数据之后从TLS请求新数据。

重点:

: 在将握手报告完成之前，连接和密钥交换
  不会在服务器上正确进行身份验证。
  即使在接收到来自客户端的第一次握手消息之后，
  1-RTT密钥对于服务器是可用的，但服务器在
  接收并验证客户端的完成消息之前，
  不能考虑对客户端进行身份验证。

: 服务器等待客户端完成消息的要求创建了对正在传递的消息的依赖性。
  客户端可以通过发送在多个分组中
  携带完成消息的CRYPTO帧的副本来
  避免潜在的行头阻塞。
  这使得服务器能够立即对
  这些数据包进行处理。


### 加密级别变更

当新加密级别的密钥可用时，
TLS会为QUIC提供这些密钥。
另外，当TLS开始使用给
定加密级别的密钥时，
TLS向QUIC指示它现在
正在使用该加密级别的密钥进行读取或写入。
这些事件不是异步的；
它们总是在为TLS提供新的
握手字节之后，
或者在TLS生成握手字节之后立即发生。

TLS provides QUIC with three items as a new encryption level becomes available:
当新的加密级别可用时，TLS为QUIC提供了下列三项:

* 一个秘钥

* 具有关联数据的认证加密(AEAD)功能

* 密钥导出函数(KDF)

这些值基于TLS协商，
QUIC使用这些值生成数据包和
报头保护密钥
(请参阅{{packet-protection}}和{{header-protect}})。

如果0-RTT是可能的，
则在客户端发送TLS ClientHello消息
或服务器接收到该消息后，它就准备好了。
在向QUIC客户端提供第一个握手字节之后，
TLS堆栈可能用信号通知0-RTT密钥的改变。
在服务器上，在接收到包含
ClientHello消息的握手字节后，
TLS服务器可能会发信号通知0-RTT密钥可用。

尽管TLS一次只使用一个加密级别，
但QUIC可以使用多个级别。
例如，在发送其完成的消息
(使用握手加密级别的CRYPTO帧)后，
终端可以发送流数据(采用1-RTT加密)。
如果完成的消息丢失，
终端使用握手加密级别重新传输丢失的消息。
重新排序或丢失数据包可能
意味着QUIC需要在多个加密级别处理数据包。
在握手期间，这意味着可能
以高于和低于TLS使用的当前加密级别的
加密级别处理数据包。

特别是，服务器实现需要能够
在0-RTT加密级别的同时
以握手加密级别读取分组。
客户端可以将用握手密钥
保护的ACK帧与0-RTT数据
交织，并且服务器需要
处理那些确认以便检测丢失的
握手分组。


### TLS接口摘要

{{exchange-summary}} 总结了客户端和服务器的QUIC和TLS之间的交换。
每个箭头都标记有用于该传输的加密级别。

~~~
Client                                                    Server

Get Handshake
                     Initial ------------->
Rekey tx to 0-RTT Keys
                     0-RTT --------------->
                                              Handshake Received
                                                   Get Handshake
                     <------------- Initial
                                          Rekey rx to 0-RTT keys
                                              Handshake Received
                                      Rekey rx to Handshake keys
                                                   Get Handshake
                     <----------- Handshake
                                          Rekey tx to 1-RTT keys
                     <--------------- 1-RTT
Handshake Received
Rekey rx to Handshake keys
Handshake Received
Get Handshake
Handshake Complete
                     Handshake ----------->
Rekey tx to 1-RTT keys
                     1-RTT --------------->
                                              Handshake Received
                                          Rekey rx to 1-RTT keys
                                                   Get Handshake
                                              Handshake Complete
                     <--------------- 1-RTT
Handshake Received
~~~
{: #exchange-summary title="Interaction Summary between QUIC and TLS"}


## TLS版本(TLS Version) {#tls-version}

本文档描述TLS 1.3 {{!TLS13}}如何与QUIC一起使用。

实际上，TLS握手将协商要使用的TLS版本。
如果收发终端均支持新版本，这可能导致终端间协商的TLS版本比1.3更高。
这是可以接受的，前提是新版本支持QUIC使用的TLS 1.3的功能。

配置错误的TLS实施会导致协商TLS 1.2或其他旧版本的TLS。
端点**必须**终止协商旧于1.3的TLS版本连接。


## ClientHello大小(ClientHello Size) {#clienthello-size}

QUIC要求来自客户端的第一个初始数据包包含整个加密握手消息，对于TLS，它是ClientHello。
虽然路径可能支持大于1200字节的数据包，但如果确保第一个ClientHello消息足够小以保持在此限制内，则客户端数据包被接受的可能性会提高。

QUIC数据包和成帧中，ClientHello消息至少需要增加36个字节的开销。
如果客户端选择非零长度的连接ID，则开销会增加。
开销也不包括令牌或长度超过8个字节的连接ID（如果服务器发送重试数据包时可能需要令牌和连接id这两项）。

典型的TLS ClientHello可以很容易地装入1200字节的数据包。
但是，除了QUIC添加的开销之外，还有一些变量可能导致大小超出此限制。
大型会话票证，多个或大型密钥共享以及支持的加密算法，签名算法，版本列表，QUIC传输参数以及其他可协商参数和扩展的长列表均可能会导致此消息增大。

对于服务器来说，除了连接ID和令牌之外，TLS会话票证的大小可能会影响客户端的连接能力。 
最小化这些值增加了客户端成功使用它们的可能性。

客户端不需要将响应HelloRetryRequest消息而发送的ClientHello放入单个UDP数据报中。

TLS实现不需要确保ClientHello足够大。
可以根据需要
添加QUIC PADDING帧增加数据包的大小。


## 对等身份验证(Peer Authentication)

身份验证的要求取决于正在使用的应用程序协议。
TLS提供服务器身份验证并允许服务器请求客户端身份验证。

客户端**必须**验证服务器的身份。 
这通常涉及验证服务器的身份是否包含在证书中以及证书是否由可信实体颁发(例如{{?RFC2818}})。

服务器**可能**请求客户端在握手期间进行身份验证。
如果客户端在请求时无法进行身份验证，则服务器**可能**拒绝连接。
客户端身份验证的要求因应用程序协议和部署而异。

服务器**禁止**使用后握手客户端身份验证 (参见{{!TLS13}}的4.6.2节).


## 启用0-RTT(Enabling 0-RTT) {#enable-0rtt}

为了可用于0-RTT，TLS必须提供一个NewSessionTicket消息，其中包含max_early_data_size为0xffffffff的“early_data”扩展;客户端可以在0-RTT中发送的数据量由服务器提供的“initial_max_data”传输参数控制。

当其中包含任何其他值时，客户端**必须**将包含“early_data”扩展名的NewSessionTicket的接收视为PROTOCOL_VIOLATION类型的连接错误。

**禁止**使用TLS连接中的早期数据。
与其他TLS应用程序数据一样，服务器**必须**将接收TLS连接上的早期数据视为PROTOCOL_VIOLATION类型的连接错误。


## 拒绝0-RTT(Rejecting 0-RTT)

服务器通过拒绝TLS层的0-RTT来拒绝
0-RTT。 
这也会阻止QUIC发送0-RTT数据。
如果服务器发送TLS HelloRetryRequest，它将始终拒绝0-RTT。

当拒绝0-RTT时，客户端假定的所有连接特性可能都不正确。
这包括应用程序协议，传输参数和任何应用程序配置的选择。
因此，客户端必须重置所有流的状态，包括绑定到这些流的应用程序状态。

如果客户端收到重试或版本协商数据包，则**可能**尝试再次发送0-RTT。
这些数据包并不表示拒绝0-RTT。

## HelloRetryRequest

在TLS over TCP中，HelloRetryRequest功能（参见{{!TLS13}}的4.1.4节）可用于纠正客户端错误的KeyShare扩展以及无状态往返检查。
从QUIC的角度来看，这看起来就像初始加密级别中携带的其他消息。
虽然原则上可以在QUIC中使用此功能进行地址验证，但QUIC实现**应该**使用重试功能(参见{{QUIC-TRANSPORT}}的8.1节). 
HelloRetryRequest仍用于请求密钥共享。

## TLS错误(TLS Errors)

如果TLS遇到错误，它会生成{{!TLS13}}第6节中定义的适当alert。

通过将单字节alert描述转换为QUIC错误代码，TLS警报将变为QUIC连接错误。
警报描述被添加到0x100以生成QUIC错误代码（从为CRYPTO_ERROR保留的范围中）。
结果值在QUIC CONNECTION_CLOSE帧中发送。

所有TLS alert的警报级别都是“fatal”;TLS堆栈**禁止**在“warn”级别生成alerts。


## 丢弃未使用的密钥( Discarding Unused Keys)

在QUIC移动到新的加密级别之后，可以丢弃先前加密级别的数据包保护密钥。
在握手期间以及更新密钥时会发生这种情况（参见{{key-update}})。
初始数据包保护密钥会被特殊处理，请参见{{discard-initial}}.

当新密钥可用时，不会立即丢弃数据包保护密钥。如果来自较低加
密级别的数据包包含CRYPTO帧，则重传该数据的帧必须以相同的加密
级别发送。类似地，端上会生成与正被确认的数据包处于相同加密级
别的数据包的确认。因此，在较新加密级别的密钥可用之后，
短时间内可能需要用于较低加密级别的密钥。

端上不能丢弃给定加密级别的密钥，除非它既接收并确认了该加密级
别的所有CRYPTO帧，并且该加密级别的所有CRYPTO帧都已被其对端确认。
但是，这并不能保证在该加密级别不需要接收或发送其他数据包，
因为对端可能尚未收到达到相同状态所需的所有确认。

在发送了给定加密级别的所有CRYPTO帧并且接收到所有预期的CRYPTO
帧，同时已经接收或发送了所有相应的确认之后，端点启动定时器。
对于不携带CRYPTO帧的0-RTT密钥，此计时器在发送或接收到受1-RTT
保护的第一个数据包时启动。为了限制密钥更改时间段内
数据包丢失的影响，端点**必须**保留该加密级别的数据包保护密钥
[QUIC-RECOVERY]中定义的当前探测超时（PTO）间隔的至少三倍。
此间隔保留的密钥允许在确定丢失数据包或新数据包需要确认时发
送包含该加密级别的CRYPTO或ACK帧的数据包。

虽然端上可能会保留旧密钥，但必须以当前可用的最高加密级
别发送新数据。仅ACK帧和CRYPTO帧中的数据重传会以先前加密级别发
送。这些数据包也**可以**包括PADDING帧。

一旦此计时器到期，端点**禁止**使用这些数据包保护密钥接受或
生成新数据包。端上可以丢弃该加密级别的数据包保护密钥。

密钥更新（参见{{key-update}})可用于其他加
密级别的密钥丢弃之前更新1-RTT密钥。在这种情况下，使用最
新的密钥保护的数据包和之前发送两次更新的数据
包表现为使用相同的密钥。握手完成后，端点只需要维护两组最
新的数据包保护密钥，并且可以丢弃旧密钥。如果数据包显
着延迟，快速多次更新密钥可能会导致数据包丢失。
由于每次往返时间只能执行一次密钥更新，因此只有延迟超过一次
往返时间的数据包才会因密钥更换而丢失;在此之前，这些数据
包将被标记为丢失，因为它们会在数据包编号序列中留下间隙。

## 丢弃初始密钥 {#discard-initial}

受初始机密保护的数据包({{initial-secrets}})未经过身份验
证，这意味着攻击者可能会破坏数据包，意图破坏连接。
为了限制这些攻击，可以比其他密钥更积极地丢弃初
始数据包保护密钥。

握手数据包的成功使用表明不再需要交换初始数据包，
因为这些密钥只能在从Initial数据包接收到所有CRYPTO帧
之后产生。因此，客户端**必须**在首次发送握手数据包时
丢弃初始密钥，并且服务器**必须**在首次成功处理握手数据
包时丢弃初始密钥。在此之后，端上**禁止**发送初始数据包。

这导致放弃初始加密级别的丢失恢复状态并忽略任何
未完成的初始数据包。

# 数据包保护{#packet-protection}

与TCP上的TLS一样，QUIC使用TLS协商的AEAD算法来保护
包含由TLS握手生成的密钥的数据包。

## 数据包保护密钥{#protection-keys}

QUIC以与TLS派生记录保护密钥相同的方式派生数据包保护密钥。

每个加密级别都有单独的密钥，用于保护在每个方向上发
送的数据包。这些流量密钥由TLS派生（参见{{!TLS13}}的第7.1节）
，并由QUIC用于除初始加密级别之外的所有加密级别。初始加密级
别的密钥是根据客户端的初始目标连接ID计算的，如{{initial-secrets}}所述。

用于分组保护的密钥是使用TLS提供的KDF从TLS密钥计算的。
在TLS 1.3中，如{{!TLS13}}的第7.1节中描述的HKDF-Expand-Label
函数，使用来自协商密码套件的散列算法。其他版本的TLS必须提
供类似的功能才能与QUIC一起使用。

将当前加密级别秘密和标签“quic key”输入到KDF以产生AEAD密钥;
标签“quic iv”用于推导IV，见{{aead}}。头部保护密钥使用“quic
hp”标签，请参见{{header-protect}}。使用这些标签提供了QUIC
和TLS之间的密钥分离，请参见{{key-diversity}}

用于初始密钥的KDF始终是TLS 1.3中的HKDF-Expand-Label函数
（参见{{initial-secrets}})）。

## 初始密钥 {#initial-secrets}

初始数据包受到来自客户端连接的第一个初始数据包的目标连接
ID字段派生的密钥的保护。规范如下：

~~~
initial_salt = 0xef4fb0abb47470c41befcf8031334fae485e09a0
initial_secret = HKDF-Extract(initial_salt,
                              client_dst_connection_id)

client_initial_secret = HKDF-Expand-Label(initial_secret,
                                          "client in", "",
                                          Hash.length)
server_initial_secret = HKDF-Expand-Label(initial_secret,
                                          "server in", "",
                                          Hash.length)
~~~

导出初始secret和key时使用的HKDF哈希函数是SHA-256
{{!SHA=DOI.10.6028/NIST.FIPS.180-4}}.

与HKDF-Expand-Label一起使用的连接ID是客户端发送的
Initial数据包中的目标连接ID。这将是一个随机选择的值，
除非客户端在收到重试数据包后创建初始数据包，那么由
服务器选择目标连接ID。

initial_salt的值是一个20字节的序列，以十六进制表示法
显示在图中。 QUIC的未来版本**应该**生成一个新的salt值，从
而确保每个版本的QUIC的密钥都不同。这可以防止仅识别一
个版本的QUIC的中间件查看或修改来自未来版本的数据包的内容。

TLS 1.3中定义的HKDF-Expand-Label函数**必须**用于初始数据
包，即使提供的TLS版本不包括TLS 1.3。

{{test-vectors-initial}} 包含初始数据包加密的测试向量。

注意：
目标连接ID具有任意长度，如果服务器发送具有零长度源连接
ID字段的重试数据包，则它可以是零长度。在这种情况下，初
始密钥不向客户端保证客户端服务器收到其数据包;客户端必须依赖包
含该属性的重试数据包的交换。

## AEAD Usage {#aead}

The Authentication Encryption with Associated Data (AEAD) {{!AEAD}} function
used for QUIC packet protection is the AEAD that is negotiated for use with the
TLS connection.  For example, if TLS is using the TLS_AES_128_GCM_SHA256, the
AEAD_AES_128_GCM function is used.

Packets are protected prior to applying header protection ({{header-protect}}).
The unprotected packet header is part of the associated data (A).  When removing
packet protection, an endpoint first removes the header protection.

All QUIC packets other than Version Negotiation and Retry packets are protected
with an AEAD algorithm {{!AEAD}}. Prior to establishing a shared secret, packets
are protected with AEAD_AES_128_GCM and a key derived from the Destination
Connection ID in the client's first Initial packet (see {{initial-secrets}}).
This provides protection against off-path attackers and robustness against QUIC
version unaware middleboxes, but not against on-path attackers.

QUIC can use any of the ciphersuites defined in {{!TLS13}} with the exception of
TLS_AES_128_CCM_8_SHA256.  The AEAD for that ciphersuite, AEAD_AES_128_CCM_8
{{?CCM=RFC6655}}, does not produce a large enough authentication tag for use
with the header protection designs provided (see {{header-protect}}).  All other
ciphersuites defined in {{!TLS13}} have a 16-byte authentication tag and produce
an output 16 bytes larger than their input.

The key and IV for the packet are computed as described in {{protection-keys}}.
The nonce, N, is formed by combining the packet protection IV with the packet
number.  The 62 bits of the reconstructed QUIC packet number in network byte
order are left-padded with zeros to the size of the IV.  The exclusive OR of the
padded packet number and the IV forms the AEAD nonce.

The associated data, A, for the AEAD is the contents of the QUIC header,
starting from the flags byte in either the short or long header, up to and
including the unprotected packet number.

The input plaintext, P, for the AEAD is the payload of the QUIC packet, as
described in {{QUIC-TRANSPORT}}.

The output ciphertext, C, of the AEAD is transmitted in place of P.

Some AEAD functions have limits for how many packets can be encrypted under the
same key and IV (see for example {{AEBounds}}).  This might be lower than the
packet number limit.  An endpoint MUST initiate a key update ({{key-update}})
prior to exceeding any limit set for the AEAD that is in use.


## Header Protection {#header-protect}

Parts of QUIC packet headers, in particular the Packet Number field, are
protected using a key that is derived separate to the packet protection key and
IV.  The key derived using the "quic hp" label is used to provide
confidentiality protection for those fields that are not exposed to on-path
elements.

This protection applies to the least-significant bits of the first byte, plus
the Packet Number field.  The four least-significant bits of the first byte are
protected for packets with long headers; the five least significant bits of the
first byte are protected for packets with short headers.  For both header forms,
this covers the reserved bits and the Packet Number Length field; the Key Phase
bit is also protected for packets with a short header.

The same header protection key is used for the duration of the connection, with
the value not changing after a key update (see {{key-update}}).  This allows
header protection to be used to protect the key phase.

This process does not apply to Retry or Version Negotiation packets, which do
not contain a protected payload or any of the fields that are protected by this
process.


### Header Protection Application

Header protection is applied after packet protection is applied (see {{aead}}).
The ciphertext of the packet is sampled and used as input to an encryption
algorithm.  The algorithm used depends on the negotiated AEAD.

The output of this algorithm is a 5 byte mask which is applied to the protected
header fields using exclusive OR.  The least significant bits of the first byte
of the packet are masked by the least significant bits of the first mask byte,
and the packet number is masked with the remaining bytes.  Any unused bytes of
mask that might result from a shorter packet number encoding are unused.

{{pseudo-hp}} shows a sample algorithm for applying header protection. Removing
header protection only differs in the order in which the packet number length
(pn_length) is determined.

~~~
mask = header_protection(hp_key, sample)

pn_length = (packet[0] & 0x03) + 1
if (packet[0] & 0x80) == 0x80:
   # Long header: 4 bits masked
   packet[0] ^= mask[0] & 0x0f
else:
   # Short header: 5 bits masked
   packet[0] ^= mask[0] & 0x1f

# pn_offset is the start of the Packet Number field.
packet[pn_offset:pn_offset+pn_length] ^= mask[1:1+pn_length]
~~~
{: #pseudo-hp title="Header Protection Pseudocode"}

{{fig-sample}} shows the protected fields of long and short headers marked with
an E.  {{fig-sample}} also shows the sampled fields.

~~~
Long Header:
+-+-+-+-+-+-+-+-+
|1|1|T T|E E E E|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Version -> Length Fields                 ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Short Header:
+-+-+-+-+-+-+-+-+
|0|1|S|E E E E E|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|               Destination Connection ID (0/32..144)         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Common Fields:
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|E E E E E E E E E  Packet Number (8/16/24/32) E E E E E E E E...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   [Protected Payload (8/16/24)]             ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|             Sampled part of Protected Payload (128)         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                 Protected Payload Remainder (*)             ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #fig-sample title="Header Protection and Ciphertext Sample"}

Before a TLS ciphersuite can be used with QUIC, a header protection algorithm
MUST be specified for the AEAD used with that ciphersuite.  This document
defines algorithms for AEAD_AES_128_GCM, AEAD_AES_128_CCM, AEAD_AES_256_GCM,
AEAD_AES_256_CCM (all AES AEADs are defined in {{!AEAD=RFC5116}}), and
AEAD_CHACHA20_POLY1305 {{!CHACHA=RFC8439}}.  Prior to TLS selecting a
ciphersuite, AES header protection is used ({{hp-aes}}), matching the
AEAD_AES_128_GCM packet protection.


### Header Protection Sample {#hp-sample}

The header protection algorithm uses both the header protection key and a sample
of the ciphertext from the packet Payload field.

The same number of bytes are always sampled, but an allowance needs to be made
for the endpoint removing protection, which will not know the length of the
Packet Number field.  In sampling the packet ciphertext, the Packet Number field
is assumed to be 4 bytes long (its maximum possible encoded length).

An endpoint MUST discard packets that are not long enough to contain a complete
sample.

To ensure that sufficient data is available for sampling, packets are padded so
that the combined lengths of the encoded packet number and protected payload is
at least 4 bytes longer than the sample required for header protection.  For the
AEAD functions defined in {{?TLS13}}, which have 16-byte expansions and 16-byte
header protection samples, this results in needing at least 3 bytes of frames in
the unprotected payload if the packet number is encoded on a single byte, or 2
bytes of frames for a 2-byte packet number encoding.

The sampled ciphertext for a packet with a short header can be determined by the
following pseudocode:

~~~
sample_offset = 1 + len(connection_id) + 4

sample = packet[sample_offset..sample_offset+sample_length]
~~~

For example, for a packet with a short header, an 8 byte connection ID, and
protected with AEAD_AES_128_GCM, the sample takes bytes 13 to 28 inclusive
(using zero-based indexing).

A packet with a long header is sampled in the same way, noting that multiple
QUIC packets might be included in the same UDP datagram and that each one is
handled separately.

~~~
sample_offset = 6 + len(destination_connection_id) +
                    len(source_connection_id) +
                    len(payload_length) + 4
if packet_type == Initial:
    sample_offset += len(token_length) +
                     len(token)

sample = packet[sample_offset..sample_offset+sample_length]
~~~


### AES-Based Header Protection {#hp-aes}

This section defines the packet protection algorithm for AEAD_AES_128_GCM,
AEAD_AES_128_CCM, AEAD_AES_256_GCM, and AEAD_AES_256_CCM. AEAD_AES_128_GCM and
AEAD_AES_128_CCM use 128-bit AES {{!AES=DOI.10.6028/NIST.FIPS.197}} in
electronic code-book (ECB) mode. AEAD_AES_256_GCM, and AEAD_AES_256_CCM use
256-bit AES in ECB mode.

This algorithm samples 16 bytes from the packet ciphertext. This value is used
as the input to AES-ECB.  In pseudocode:

~~~
mask = AES-ECB(hp_key, sample)
~~~


### ChaCha20-Based Header Protection {#hp-chacha}

When AEAD_CHACHA20_POLY1305 is in use, header protection uses the raw ChaCha20
function as defined in Section 2.4 of {{!CHACHA}}.  This uses a 256-bit key and
16 bytes sampled from the packet protection output.

The first 4 bytes of the sampled ciphertext are interpreted as a 32-bit number
in little-endian order and are used as the block count.  The remaining 12 bytes
are interpreted as three concatenated 32-bit numbers in little-endian order and
used as the nonce.

The encryption mask is produced by invoking ChaCha20 to protect 5 zero bytes. In
pseudocode:

~~~
counter = DecodeLE(sample[0..3])
nonce = DecodeLE(sample[4..7], sample[8..11], sample[12..15])
mask = ChaCha20(hp_key, counter, nonce, {0,0,0,0,0})
~~~


## Receiving Protected Packets

Once an endpoint successfully receives a packet with a given packet number, it
MUST discard all packets in the same packet number space with higher packet
numbers if they cannot be successfully unprotected with either the same key, or
- if there is a key update - the next packet protection key (see
{{key-update}}).  Similarly, a packet that appears to trigger a key update, but
cannot be unprotected successfully MUST be discarded.

Failure to unprotect a packet does not necessarily indicate the existence of a
protocol error in a peer or an attack.  The truncated packet number encoding
used in QUIC can cause packet numbers to be decoded incorrectly if they are
delayed significantly.


## Use of 0-RTT Keys {#using-early-data}

If 0-RTT keys are available (see {{enable-0rtt}}), the lack of replay protection
means that restrictions on their use are necessary to avoid replay attacks on
the protocol.

A client MUST only use 0-RTT keys to protect data that is idempotent.  A client
MAY wish to apply additional restrictions on what data it sends prior to the
completion of the TLS handshake.  A client otherwise treats 0-RTT keys as
equivalent to 1-RTT keys, except that it MUST NOT send ACKs with 0-RTT keys.

A client that receives an indication that its 0-RTT data has been accepted by a
server can send 0-RTT data until it receives all of the server's handshake
messages.  A client SHOULD stop sending 0-RTT data if it receives an indication
that 0-RTT data has been rejected.

A server MUST NOT use 0-RTT keys to protect packets; it uses 1-RTT keys to
protect acknowledgements of 0-RTT packets.  A client MUST NOT attempt to
decrypt 0-RTT packets it receives and instead MUST discard them.

Note:

: 0-RTT data can be acknowledged by the server as it receives it, but any
  packets containing acknowledgments of 0-RTT data cannot have packet protection
  removed by the client until the TLS handshake is complete.  The 1-RTT keys
  necessary to remove packet protection cannot be derived until the client
  receives all server handshake messages.


## Receiving Out-of-Order Protected Frames {#pre-hs-protected}

Due to reordering and loss, protected packets might be received by an endpoint
before the final TLS handshake messages are received.  A client will be unable
to decrypt 1-RTT packets from the server, whereas a server will be able to
decrypt 1-RTT packets from the client.

However, a server MUST NOT process data from incoming 1-RTT protected packets
before verifying either the client Finished message or - in the case that the
server has chosen to use a pre-shared key - the pre-shared key binder (see
Section 4.2.11 of {{!TLS13}}).  Verifying these values provides the server with
an assurance that the ClientHello has not been modified.  Packets protected with
1-RTT keys MAY be stored and later decrypted and used once the handshake is
complete.

A server could receive packets protected with 0-RTT keys prior to receiving a
TLS ClientHello.  The server MAY retain these packets for later decryption in
anticipation of receiving a ClientHello.


# Key Update

Once the 1-RTT keys are established and the short header is in use, it is
possible to update the keys. The KEY_PHASE bit in the short header is used to
indicate whether key updates have occurred. The KEY_PHASE bit is initially set
to 0 and then inverted with each key update.

The KEY_PHASE bit allows a recipient to detect a change in keying material
without necessarily needing to receive the first packet that triggered the
change.  An endpoint that notices a changed KEY_PHASE bit can update keys and
decrypt the packet that contains the changed bit.

This mechanism replaces the TLS KeyUpdate message.  Endpoints MUST NOT send a
TLS KeyUpdate message.  Endpoints MUST treat the receipt of a TLS KeyUpdate
message as a connection error of type 0x10a, equivalent to a fatal TLS alert of
unexpected_message (see {{tls-errors}}).

An endpoint MUST NOT initiate more than one key update at a time.  A new key
cannot be used until the endpoint has received and successfully decrypted a
packet with a matching KEY_PHASE.

A receiving endpoint detects an update when the KEY_PHASE bit does not match
what it is expecting.  It creates a new secret (see Section 7.2 of {{!TLS13}})
and the corresponding read key and IV using the KDF function provided by TLS.
The header protection key is not updated.

If the packet can be decrypted and authenticated using the updated key and IV,
then the keys the endpoint uses for packet protection are also updated.  The
next packet sent by the endpoint will then use the new keys.

An endpoint does not always need to send packets when it detects that its peer
has updated keys.  The next packet that it sends will simply use the new keys.
If an endpoint detects a second update before it has sent any packets with
updated keys, it indicates that its peer has updated keys twice without awaiting
a reciprocal update.  An endpoint MUST treat consecutive key updates as a fatal
error and abort the connection.

An endpoint SHOULD retain old keys for a period of no more than three times the
Probe Timeout (PTO, see {{QUIC-RECOVERY}}).  After this period, old keys and
their corresponding secrets SHOULD be discarded.  Retaining keys allow endpoints
to process packets that were sent with old keys and delayed in the network.
Packets with higher packet numbers always use the updated keys and MUST NOT be
decrypted with old keys.

This ensures that once the handshake is complete, packets with the same
KEY_PHASE will have the same packet protection keys, unless there are multiple
key updates in a short time frame succession and significant packet reordering.

~~~
   Initiating Peer                    Responding Peer

@M QUIC Frames
               New Keys -> @N
@N QUIC Frames
                      -------->
                                          QUIC Frames @M
                          New Keys -> @N
                                          QUIC Frames @N
                      <--------
~~~
{: #ex-key-update title="Key Update"}

A packet that triggers a key update could arrive after successfully processing a
packet with a higher packet number.  This is only possible if there is a key
compromise and an attack, or if the peer is incorrectly reverting to use of old
keys.  Because the latter cannot be differentiated from an attack, an endpoint
MUST immediately terminate the connection if it detects this condition.

In deciding when to update keys, endpoints MUST NOT exceed the limits for use of
specific keys, as described in Section 5.5 of {{!TLS13}}.


# 初始消息的安全性(Security of Initial Messages)

初始数据包不受密钥保护，因此它们易受到攻击者的可能的篡改。
QUIC 提供针对无法读取数据包的攻击者的保护，但不尝试提供此外的保护，如防止攻击者可以观察和注入数据包的情况下攻击。
某些形式的篡改 -- 例如修改 TLS 消息本身 -- 是可检测的，但有些 -- 例如修改 ACK -- 是不可检测的。

例如，攻击者可以注入包含 ACK 帧的分组，该 ACK 帧使分组看起来没有被接收到，或者造成连接状态的错误印象(例如，通过修改ACK延迟)。
值得注意的是，这样的数据包可能会导致合法数据包作为副本被丢弃。
实现**应该**谨慎依赖包含在未进行身份验证的初始数据包中的任何数据。

攻击者也可能篡改握手数据包中携带的数据，但由于篡改需要修改 TLS 握手消息，因此篡改将导致 TLS 握手失败。


# QUIC对TLS握手的额外特性(QUIC-Specific Additions to the TLS Handshake)

QUIC 使用 TLS 握手不仅仅用于加密参数的协商。
TLS 握手会验证协议版本选择，提供 QUIC 传输参数的初始值，并允许服务端让客户端执行返回可路由性检查。

## 协议和版本协商(Protocol and Version Negotiation) {#version-negotiation}

QUIC 版本协商机制用于协商完成握手之前使用的 QUIC 版本。
然而此数据包是未经过身份验证的，这使得主动攻击者能够强制版本降级。

为了确保 QUIC 版本降级不是被攻击者强行降级的，版本信息被拷贝到 TLS 握手中，为 QUIC 协商提供完整性保护。
这并不能防止在握手完成之前版本降级，尽管这意味着降级会导致握手失败。

QUIC 要求加密握手提供经过身份验证的协议协商。
TLS 使用应用层协议协商(ALPN){{!RFC7301}}来选择应用协议。
除非使用另一种机制来商定应用协议，否则终端**必须**为此使用 ALPN。
使用 ALPN 时，如果未协商应用协议，则终端**必须**中止连接。

应用层协议**可能**会限制它可以操作的 QUIC 版本。
服务端**必须**选择与客户端选择的 QUIC 版本兼容的应用程序协议。
如果服务端无法选择应用程序协议和 QUIC 版本的兼容组合，则**必须**中止连接。
如果服务器选择 QUIC 版本和 ALPN 标识符的不兼容的组合，则客户端**必须**中止连接。

## QUIC传输参数扩展(QUIC Transport Parameters Extension) {#quic_parameters}

QUIC 传输参数携带在 TLS 拓展中。
不同版本的 QUIC 可能给这个结构定义了不同的格式。

将传输参数包含在在 TLS 握手中提供了对这些值的完整性保护。

~~~
   enum {
      quic_transport_parameters(0xffa5), (65535)
   } ExtensionType;
~~~

`quic_transport_parameters`的扩展`extension_data`字段包含由正在使用的 QUIC 版本定义的值。
使用{{QUIC-TRANSPORT}}中定义的 QUIC 版本时，
`quic_transport_parameters`扩展会携带传输参数结构(TransportParameters)。

`quic_transport_parameters`扩展在握手期间在 ClientHello 和 EncryptedExtensions 消息中携带。

虽然在握手完成之前传输参数在技术上是可用的，但在握手完成之前不能完全信任它们，并且应该尽量减少对它们的依赖。
然而，对参数的任何篡改都会导致握手失败。

终端**禁止**在不使用 QUIC 的 TLS 连接(例如使用定义在{{!TLS13}}中的带有 TLS 的 TCP )中发送该拓展。
如果在传输协议不是 QUIC 时收到此扩展，则**必须**发送不支持拓展警报的致命错误。

## 移除前期数据的末尾消息(Removing the EndOfEarlyData Message) {#remove-eoed}

TLS EndOfEarlyData 消息未与 QUIC 一起使用。
QUIC 不依赖于此消息来标记 0-RTT 数据的结束，也不依赖于用信号通知对握手密钥的更改。

客户端**禁止**发送 EndOfEarlyData 消息。
服务端**必须**以 PROTOCOL_VIOLATION 类型的连接错误来处理在 0-RTT 包中接收到的 CRYPTO 帧。

因此，EndOfEarlyData 不会出现在 TLS 握手记录中。


# 安全相关考虑(Security Considerations)

这里最终可能会出现一些真正的问题，但当前的一系列问题在正文的相关章节中得到了很好的处理。

永远不要假设因为它不在安全注意事项部分，它就不会影响安全性。
本文档的大部分内容都是如此。

## 包反射攻击缓解(Packet Reflection Attack Mitigation) {#reflection}

来自服务器的大量握手消息的小 ClientHello 可用于包反射攻击，以放大攻击者生成的通信量。

QUIC 包含三种防御此攻击的方法。
首先，ClientHello 包**必须**被填充到最小大小。
其次，如果响应未经验证的源地址，则禁止服务端在第一次交互中发送三个以上的 UDP 数据报(参见{{QUIC-TRANSPORT}}的第8.1节)。
最后，因为握手数据包的确认是经过身份验证的，所以无信息攻击者(blind attacker)无法伪造它们。
总而言之，这些防御措施限制了扩增的水平。

## Peer Denial of Service {#useless}

QUIC, TLS, and HTTP/2 all contain messages that have legitimate uses in some
contexts, but that can be abused to cause a peer to expend processing resources
without having any observable impact on the state of the connection.  If
processing is disproportionately large in comparison to the observable effects
on bandwidth or state, then this could allow a malicious peer to exhaust
processing capacity without consequence.

QUIC prohibits the sending of empty `STREAM` frames unless they are marked with
the FIN bit.  This prevents `STREAM` frames from being sent that only waste
effort.

While there are legitimate uses for some redundant packets, implementations
SHOULD track redundant packets and treat excessive volumes of any non-productive
packets as indicative of an attack.


## Header Protection Analysis {#header-protect-analysis}

Header protection relies on the packet protection AEAD being a pseudorandom
function (PRF), which is not a property that AEAD algorithms
guarantee. Therefore, no strong assurances about the general security of this
mechanism can be shown in the general case. The AEAD algorithms described in
this document are assumed to be PRFs.

The header protection algorithms defined in this document take the form:

~~~
protected_field = field XOR PRF(hp_key, sample)
~~~

This construction is secure against chosen plaintext attacks (IND-CPA) {{IMC}}.

Use of the same key and ciphertext sample more than once risks compromising
header protection. Protecting two different headers with the same key and
ciphertext sample reveals the exclusive OR of the protected fields.  Assuming
that the AEAD acts as a PRF, if L bits are sampled, the odds of two ciphertext
samples being identical approach 2^(-L/2), that is, the birthday bound. For the
algorithms described in this document, that probability is one in 2^64.

Note:

: In some cases, inputs shorter than the full size required by the packet
  protection algorithm might be used.

To prevent an attacker from modifying packet headers, the header is transitively
authenticated using packet protection; the entire packet header is part of the
authenticated additional data.  Protected fields that are falsified or modified
can only be detected once the packet protection is removed.

An attacker could guess values for packet numbers and have an endpoint confirm
guesses through timing side channels.  Similarly, guesses for the packet number
length can be trialed and exposed.  If the recipient of a packet discards
packets with duplicate packet numbers without attempting to remove packet
protection they could reveal through timing side-channels that the packet number
matches a received packet.  For authentication to be free from side-channels,
the entire process of header protection removal, packet number recovery, and
packet protection removal MUST be applied together without timing and other
side-channels.

For the sending of packets, construction and protection of packet payloads and
packet numbers MUST be free from side-channels that would reveal the packet
number or its encoded size.


## Key Diversity

In using TLS, the central key schedule of TLS is used.  As a result of the TLS
handshake messages being integrated into the calculation of secrets, the
inclusion of the QUIC transport parameters extension ensures that handshake and
1-RTT keys are not the same as those that might be produced by a server running
TLS over TCP.  To avoid the possibility of cross-protocol key synchronization,
additional measures are provided to improve key separation.

The QUIC packet protection keys and IVs are derived using a different label than
the equivalent keys in TLS.

To preserve this separation, a new version of QUIC SHOULD define new labels for
key derivation for packet protection key and IV, plus the header protection
keys.  This version of QUIC uses the string "quic".  Other versions can use a
version-specific label in place of that string.

The initial secrets use a key that is specific to the negotiated QUIC version.
New QUIC versions SHOULD define a new salt value used in calculating initial
secrets.


# IANA Considerations

This document does not create any new IANA registries, but it registers the
values in the following registries:

* TLS ExtensionsType Registry {{!TLS-REGISTRIES=RFC8447}} - IANA is to register
  the quic_transport_parameters extension found in {{quic_parameters}}.  The
  Recommended column is to be marked Yes.  The TLS 1.3 Column is to include CH
  and EE.


--- back

# Sample Initial Packet Protection {#test-vectors-initial}

This section shows examples of packet protection for Initial packets so that
implementations can be verified incrementally.  These packets use an 8-byte
client-chosen Destination Connection ID of 0x8394c8f03e515708.  Values for both
server and client packet protection are shown together with values in
hexadecimal.


## Keys

The labels generated by the HKDF-Expand-Label function are:

client in:
: 00200f746c73313320636c69656e7420696e00

server in:
: 00200f746c7331332073657276657220696e00

quic key:
: 00100e746c7331332071756963206b657900

quic iv:
: 000c0d746c733133207175696320697600

quic hp:
: 00100d746c733133207175696320687000

The initial secret is common:

~~~
initial_secret = HKDF-Extract(initial_salt, cid)
    = 4496d3903d3f97cc5e45ac5790ddc686
      683c7c0067012bb09d900cc21832d596
~~~

The secrets for protecting client packets are:

~~~
client_initial_secret
    = HKDF-Expand-Label(initial_secret, "client in", _, 32)
    = 8a3515a14ae3c31b9c2d6d5bc58538ca
      5cd2baa119087143e60887428dcb52f6

key = HKDF-Expand-Label(client_initial_secret, "quic key", _, 16)
    = 98b0d7e5e7a402c67c33f350fa65ea54

iv  = HKDF-Expand-Label(client_initial_secret, "quic iv", _, 12)
    = 19e94387805eb0b46c03a788

hp  = HKDF-Expand-Label(client_initial_secret, "quic hp", _, 16)
    = 0edd982a6ac527f2eddcbb7348dea5d7
~~~

The secrets for protecting server packets are:

~~~
server_initial_secret
    = HKDF-Expand-Label(initial_secret, "server in", _, 32)
    = 47b2eaea6c266e32c0697a9e2a898bdf
      5c4fb3e5ac34f0e549bf2c58581a3811

key = HKDF-Expand-Label(server_initial_secret, "quic key", _, 16)
    = 9a8be902a9bdd91d16064ca118045fb4

iv  = HKDF-Expand-Label(server_initial_secret, "quic iv", _, 12)
    = 0a82086d32205ba22241d8dc

hp  = HKDF-Expand-Label(server_initial_secret, "quic hp", _, 16)
    = 94b9452d2b3c7c7f6da7fdd8593537fd
~~~


## Client Initial

The client sends an Initial packet.  The unprotected payload of this packet
contains the following CRYPTO frame, plus enough PADDING frames to make an 1163
byte payload:

~~~
060040c4010000c003036660261ff947 cea49cce6cfad687f457cf1b14531ba1
4131a0e8f309a1d0b9c4000006130113 031302010000910000000b0009000006
736572766572ff01000100000a001400 12001d00170018001901000101010201
03010400230000003300260024001d00 204cfdfcd178b784bf328cae793b136f
2aedce005ff183d7bb14952072366470 37002b0003020304000d0020001e0403
05030603020308040805080604010501 060102010402050206020202002d0002
0101001c00024001
~~~

The unprotected header includes the connection ID and a 4 byte packet number
encoding for a packet number of 2:

~~~
c3ff000012508394c8f03e51570800449f00000002
~~~

Protecting the payload produces output that is sampled for header protection.
Because the header uses a 4 byte packet number encoding, the first 16 bytes of
the protected payload is sampled, then applied to the header:

~~~
sample = 0000f3a694c75775b4e546172ce9e047

mask = AES-ECB(hp, sample)[0..4]
     = 020dbc1958

header[0] ^= mask[0] & 0x0f
     = c1
header[17..20] ^= mask[1..4]
     = 0dbc195a
header = c1ff000012508394c8f03e51570800449f0dbc195a
~~~

The resulting protected packet is:

~~~
c1ff000012508394c8f03e5157080044 9f0dbc195a0000f3a694c75775b4e546
172ce9e047cd0b5bee5181648c727adc 87f7eae54473ec6cba6bdad4f5982317
4b769f12358abd292d4f3286934484fb 8b239c38732e1f3bbbc6a003056487eb
8b5c88b9fd9279ffff3b0f4ecf95c462 4db6d65d4113329ee9b0bf8cdd7c8a8d
72806d55df25ecb66488bc119d7c9a29 abaf99bb33c56b08ad8c26995f838bb3
b7a3d5c1858b8ec06b839db2dcf918d5 ea9317f1acd6b663cc8925868e2f6a1b
da546695f3c3f33175944db4a11a346a fb07e78489e509b02add51b7b203eda5
c330b03641179a31fbba9b56ce00f3d5 b5e3d7d9c5429aebb9576f2f7eacbe27
bc1b8082aaf68fb69c921aa5d33ec0c8 510410865a178d86d7e54122d55ef2c2
bbc040be46d7fece73fe8a1b24495ec1 60df2da9b20a7ba2f26dfa2a44366dbc
63de5cd7d7c94c57172fe6d79c901f02 5c0010b02c89b395402c009f62dc053b
8067a1e0ed0a1e0cf5087d7f78cbd94a fe0c3dd55d2d4b1a5cfe2b68b86264e3
51d1dcd858783a240f893f008ceed743 d969b8f735a1677ead960b1fb1ecc5ac
83c273b49288d02d7286207e663c45e1 a7baf50640c91e762941cf380ce8d79f
3e86767fbbcd25b42ef70ec334835a3a 6d792e170a432ce0cb7bde9aaa1e7563
7c1c34ae5fef4338f53db8b13a4d2df5 94efbfa08784543815c9c0d487bddfa1
539bc252cf43ec3686e9802d651cfd2a 829a06a9f332a733a4a8aed80efe3478
093fbc69c8608146b3f16f1a5c4eac93 20da49f1afa5f538ddecbbe7888f4355
12d0dd74fd9b8c99e3145ba84410d8ca 9a36dd884109e76e5fb8222a52e1473d
a168519ce7a8a3c32e9149671b16724c 6c5c51bb5cd64fb591e567fb78b10f9f
6fee62c276f282a7df6bcf7c17747bc9 a81e6c9c3b032fdd0e1c3ac9eaa5077d
e3ded18b2ed4faf328f49875af2e36ad 5ce5f6cc99ef4b60e57b3b5b9c9fcbcd
4cfb3975e70ce4c2506bcd71fef0e535 92461504e3d42c885caab21b782e2629
4c6a9d61118cc40a26f378441ceb48f3 1a362bf8502a723a36c63502229a462c
c2a3796279a5e3a7f81a68c7f81312c3 81cc16a4ab03513a51ad5b54306ec1d7
8a5e47e2b15e5b7a1438e5b8b2882dbd ad13d6a4a8c3558cae043501b68eb3b0
40067152337c051c40b5af809aca2856 986fd1c86a4ade17d254b6262ac1bc07
7343b52bf89fa27d73e3c6f3118c9961 f0bebe68a5c323c2d84b8c29a2807df6
63635223242a2ce9828d4429ac270aab 5f1841e8e49cf433b1547989f419caa3
c758fff96ded40cf3427f0761b678daa 1a9e5554465d46b7a917493fc70f9ec5
e4e5d786ca501730898aaa1151dcd318 29641e29428d90e6065511c24d3109f7
cba32225d4accfc54fec42b733f95852 52ee36fa5ea0c656934385b468eee245
315146b8c047ed27c519b2c0a52d33ef e72c186ffe0a230f505676c5324baa6a
e006a73e13aa8c39ab173ad2b2778eea 0b34c46f2b3beae2c62a2c8db238bf58
fc7c27bdceb96c56d29deec87c12351b fd5962497418716a4b915d334ffb5b92
ca94ffe1e4f78967042638639a9de325 357f5f08f6435061e5a274703936c06f
c56af92c420797499ca431a7abaa4618 63bca656facfad564e6274d4a741033a
ca1e31bf63200df41cdf41c10b912bec
~~~

## Server Initial

The server sends the following payload in response, including an ACK frame, a
CRYPTO frame, and no PADDING frames:

~~~
0d0000000018410a020000560303eefc e7f7b37ba1d1632e96677825ddf73988
cfc79825df566dc5430b9a045a120013 0100002e00330024001d00209d3c940d
89690b84d08a60993c144eca684d1081 287c834d5311bcf32bb9da1a002b0002
0304
~~~

The header from the server includes a new connection ID and a 2-byte packet
number encoding for a packet number of 1:

~~~
c1ff00001205f067a5502a4262b50040740001
~~~

As a result, after protection, the header protection sample is taken starting
from the third protected octet:

~~~
sample = c4c2a2303d297e3c519bf6b22386e3d0
mask   = 75f7ec8b62
header = c4ff00001205f067a5502a4262b5004074f7ed
~~~

The final protected packet is then:

~~~
c4ff00001205f067a5502a4262b50040 74f7ed5f01c4c2a2303d297e3c519bf6
b22386e3d0bd6dfc6612167729803104 1bb9a79c9f0f9d4c5877270a660f5da3
6207d98b73839b2fdf2ef8e7df5a51b1 7b8c68d864fd3e708c6c1b71a98a3318
15599ef5014ea38c44bdfd387c03b527 5c35e009b6238f831420047c7271281c
cb54df7884
~~~


# Change Log

> **RFC Editor's Note:** Please remove this section prior to publication of a
> final version of this document.

Issue and pull request numbers are listed with a leading octothorp.


## Since draft-ietf-quic-tls-17

- Endpoints discard initial keys as soon as handshake keys are available (#1951,
  #2045)
- Use of ALPN or equivalent is mandatory (#2263, #2284)


## Since draft-ietf-quic-tls-14

- Update the salt used for Initial secrets (#1970)
- Clarify that TLS_AES_128_CCM_8_SHA256 isn't supported (#2019)
- Change header protection
  - Sample from a fixed offset (#1575, #2030)
  - Cover part of the first byte, including the key phase (#1322, #2006)
- TLS provides an AEAD and KDF function (#2046)
  - Clarify that the TLS KDF is used with TLS (#1997)
  - Change the labels for calculation of QUIC keys (#1845, #1971, #1991)
- Initial keys are discarded once Handshake are avaialble (#1951, #2045)


## Since draft-ietf-quic-tls-13

- Updated to TLS 1.3 final (#1660)


## Since draft-ietf-quic-tls-12

- Changes to integration of the TLS handshake (#829, #1018, #1094, #1165, #1190,
  #1233, #1242, #1252, #1450)
  - The cryptographic handshake uses CRYPTO frames, not stream 0
  - QUIC packet protection is used in place of TLS record protection
  - Separate QUIC packet number spaces are used for the handshake
  - Changed Retry to be independent of the cryptographic handshake
  - Limit the use of HelloRetryRequest to address TLS needs (like key shares)
- Changed codepoint of TLS extension (#1395, #1402)


## Since draft-ietf-quic-tls-11

- Encrypted packet numbers.


## Since draft-ietf-quic-tls-10

- No significant changes.


## Since draft-ietf-quic-tls-09

- Cleaned up key schedule and updated the salt used for handshake packet
  protection (#1077)


## Since draft-ietf-quic-tls-08

- Specify value for max_early_data_size to enable 0-RTT (#942)
- Update key derivation function (#1003, #1004)


## Since draft-ietf-quic-tls-07

- Handshake errors can be reported with CONNECTION_CLOSE (#608, #891)


## Since draft-ietf-quic-tls-05

No significant changes.


## Since draft-ietf-quic-tls-04

- Update labels used in HKDF-Expand-Label to match TLS 1.3 (#642)


## Since draft-ietf-quic-tls-03

No significant changes.


## Since draft-ietf-quic-tls-02

- Updates to match changes in transport draft


## Since draft-ietf-quic-tls-01

- Use TLS alerts to signal TLS errors (#272, #374)
- Require ClientHello to fit in a single packet (#338)
- The second client handshake flight is now sent in the clear (#262, #337)
- The QUIC header is included as AEAD Associated Data (#226, #243, #302)
- Add interface necessary for client address validation (#275)
- Define peer authentication (#140)
- Require at least TLS 1.3 (#138)
- Define transport parameters as a TLS extension (#122)
- Define handling for protected packets before the handshake completes (#39)
- Decouple QUIC version and ALPN (#12)


## Since draft-ietf-quic-tls-00

- Changed bit used to signal key phase
- Updated key phase markings during the handshake
- Added TLS interface requirements section
- Moved to use of TLS exporters for key derivation
- Moved TLS error code definitions into this document

## Since draft-thomson-quic-tls-01

- Adopted as base for draft-ietf-quic-tls
- Updated authors/editors list
- Added status note


# Acknowledgments
{:numbered="false"}

This document has benefited from input from Dragana Damjanovic, Christian
Huitema, Jana Iyengar, Adam Langley, Roberto Peon, Eric Rescorla, Ian Swett, and
many others.


# Contributors
{:numbered="false"}

Ryan Hamilton was originally an author of this specification.
