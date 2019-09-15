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

# 介绍(Introduction)

本文档描述了如何使用TLS{{!TLS13=RFC8446}}保护QUIC{{QUIC-TRANSPORT}}。

与以前的版本相比，TLS 1.3为连接建立提供了关键的延迟改进。
在没有丢包的情况下，大多数新连接可以在一次往返中建立和保护;
在同一客户机和服务器之间的后续连接上，
即客户机通常可以使用零往返设置立即发送应用程序数据。

本文档描述了TLS如何作为QUIC的安全组件。


# 符号约定 (Notational Conventions)

本文件中“MUST”、“MUST NOT”、“REQUIRED”、“SHALL”、“SHALL NOT”、“SHOULD”、
“SHOULD NOT”、“RECOMMENDED”、“NOT RECOMMENDED”、“MAY”和“OPTIONAL”等关键字
必须按照BCP 14 {{!RFC2119}} {{!RFC8174}}中所述的方式解释，
且仅当它们所有都为大写字母时，就像这里展示的一样。

本文件使用了{{QUIC-TRANSPORT}} 中建立的术语。

为简洁起见，缩写TLS用于引用TLS 1.3，不过可以使用更新的版本(见{{tls-version}})。


## TLS概述 (TLS Overview)

TLS为两个端点提供了一种方法，用于在不受信任的媒介(即Internet)上建立通信手段，
以确保它们交换的消息不能被观察、修改或伪造。

在内部，TLS是一个分层协议，结构如下:

~~~~
+--------------+--------------+--------------+
|  握手协议   |    警报       |  应用数据       |
|  (Handshake|    (Alerts)  |   (Application |
|  Layer)    |              |         Data)  |
+--------------+--------------+--------------+
|                                            |
|              记录层(Record Layer)           |
|                                            |
+--------------------------------------------+
~~~~

每个上层(握手、警报和应用程序数据)都作为一系列类型的TLS记录携带。
记录被单独加密保护，然后通过可靠的传输方法(通常是TCP)传输，
该传输提供了顺序和有保证的传输。

更改密码规范记录不能用QUIC发送。

TLS认证密钥交换发生在两个实体之间:客户机和服务器。
客户机启动交换，服务器响应。如果密钥交换成功完成，客户机和服务器都将同意一个密钥。
TLS同时支持预共享密钥(PSK)和Diffie-Hellman (DH)密钥交换。
PSK是0-RTT的基;当DH密钥被销毁时，后者提供了完美的正向保密(PFS)。

在完成TLS握手之后，客户机将学习并验证服务器的标识，
服务器也可以选择学习和验证客户机的标识。
TLS支持基于X.509 {{?RFC5280}}的基于证书的服务器和客户机身份验证。

TLS密钥交换能够抵抗攻击者的篡改，
并且它产生的共享秘密不能被任何参与其中的对等方控制。

TLS提供了QUIC感兴趣的两种基本握手模式:

 * 一个完整的1-RTT握手，其中客户端能够在一次往返后发送应用程序数据，
   服务器在收到来自客户端的第一个握手消息后立即响应。


 * 0-RTT握手中客户端使用它之前了解的关于服务器的信息来立即发送应用程序数据。
   攻击者可以重放此应用程序数据，
   因此它**不能**为任何非幂等操作携带自包含触发器。

 {{tls-full}}显示了一个使用0-RTT应用程序数据的简化TLS握手。
 注意，这忽略了EndOfEarlyData消息，这在QUIC中没有使用{{remove-eoed}}。


~~~
    客户端                                             服务端

    客户端请求
   (0-RTT 应用数据)  -------->
                                                  服务端请求
                                                  {加密扩展}
                                                   {完结的}
                             <--------          [应用程序数据]
   {完结的}                -------->

   [应用程序数据]        <------->      [应用程序数据]

    () 受早期数据(0-RTT)键保护的指示消息
    {} 使用握手密钥保护的指示消息
    [] 使用应用程序数据保护的指示消息(1-RTT)键
~~~
{: #tls-full title="TLS与0-RTT握手"}

使用多个加密级别保护数据:

- 初始密钥
- 早期数据(0-RTT)键
- 握手键
- 应用数据(1-RTT)键

应用程序数据可能只出现在早期数据和应用程序数据保护级别。
握手和警报消息可以出现在任何保护级别。

0-RTT握手只有在客户端和服务器之前进行过通信时才有可能发生。
在1-RTT握手中，直到它接收到服务器发送的所有握手消息，
客户端无法发送受保护的应用程序数据。


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

为了可用于0-RTT，TLS必须提供一个NewSessionTicket消息，
其中包含max_early_data_size为0xffffffff的“early_data”扩展;
客户端可以在0-RTT中发送的数据量由服务器提供的“initial_max_data”传输参数控制。

当其中包含任何其他值时，客户端**必须**将包含“early_data”扩展名的
NewSessionTicket的接收视为PROTOCOL_VIOLATION类型的连接错误。

**禁止**使用TLS连接中的早期数据。
与其他TLS应用程序数据一样，服务器**必须**将接收TLS连接上的早期数据视为PROTOCOL_VIOLATION类型的连接错误。


## 拒绝0-RTT(Rejecting 0-RTT)

服务器通过拒绝TLS层的0-RTT来0-RTT。
这也会阻止QUIC发送0-RTT数据。
如果服务器发送TLS HelloRetryRequest，它将始终拒绝0-RTT。

当拒绝0-RTT时，客户端假定的所有连接特性可能都不正确。
这包括应用程序协议，传输参数和任何应用程序配置的选择。
因此，客户端必须重置所有流的状态，包括绑定到这些流的应用程序状态。

如果客户端收到重试或版本协商数据包，则**可能**尝试再次发送0-RTT。
这些数据包并不表示拒绝0-RTT。

## HelloRetryRequest

在TLS over TCP中，HelloRetryRequest功能（参见{{!TLS13}}的4.1.4节）
可用于纠正客户端错误的KeyShare扩展以及无状态往返检查。
从QUIC的角度来看，这看起来就像初始加密级别中携带的其他消息。
虽然原则上可以在QUIC中使用此功能进行地址验证，但QUIC实现**应该**使用重试功能(参见{{QUIC-TRANSPORT}}的8.1节).
HelloRetryRequest仍用于请求密钥共享。

## TLS错误(TLS Errors) {#tls-errors}

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
著延迟，快速多次更新密钥可能会导致数据包丢失。
由于每次往返时间只能执行一次密钥更新，因此只有延迟超过一次
往返时间的数据包才会因密钥更换而丢失;在此之前，这些数据
包将被标记为丢失，因为它们会在数据包编号序列中留下间隙。

## 丢弃初始密钥 {#discard-initial}

受初始密钥保护的数据包({{initial-secrets}})未经过身份验
证，这意味着攻击者可能会破坏("破坏"，spoof一般翻译做欺骗，建
议这里翻译为伪造等相近含义)数据包，意图破坏连接。
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

用于数据包保护的密钥是使用TLS提供的KDF从TLS密钥计算的。
在TLS 1.3中，如{{!TLS13}}的第7.1节中描述的HKDF-Expand-Label
函数，使用来自协商密码套件的散列算法。其他版本的TLS必须提
供类似的功能才能与QUIC一起使用。

将当前加密级别密钥和标签“quic key”输入到KDF以产生AEAD密钥;
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

## AEAD用法(AEAD Usage) {#aead}

用于QUIC数据包保护的具有关联数据的身份验证加密(AEAD)
{{!AEAD}}功能是协商以与TLS连接一起使用的AEAD。例如，
如果TLS使用TLS_AES_128_GCM_SHA256，则使用aead_AES_128_GCM函数。

在应用包头保护之前对数据包进行保护({{header-protect}})。未受保护的
数据包报头是关联数据(A)的一部分。当移除数据包保护时，端点首先移除报头保护。

除版本协商和重试分组之外的所有QUIC分组都使用AEAD算法{{!AEAD}}进行保护。
在建立共享密钥之前，使用aead_aes_128_gcm和从客户端的第一个初始数据包中
的目标连接ID派生的密钥来保护数据包(参见{{initial-secrets}})。这提供了针对路
径外攻击者的保护，以及针对QUIC版本无意识中间件的鲁棒性，但不能抵御路径上的攻击者。

QUIC可以使用{{!TLS13}}中定义的任何密码套件，但TLS_AES_128_CCM_8_SHA256除外。
该密码套件的AEAD（AEAD_AES_128_CCM_8{{?CCM=RFC6655}}）不会产生满足
包头保护设计要求（参见{{header-protect}}）的足够长度的认证标签。{{!TLS13}}中定义的
其他所有密码套件都有一个16字节的认证标签，产生的输出比输入大16个字节。

数据包的密钥和IV按{{protection-keys}}中的描述计算。通过将数据包保护IV与数据包号组合
来形成随机数N。以网络字节顺序重构的QUIC分组编号的62位用前导0填充到IV的尺寸。填
充分组编号和IV的异或形成AEAD随机数。

AEAD的相关数据A是QUIC报头的内容，从短报头或长报头中的标志字节开始，直到并包括
不受保护的数据包号。

AEAD的输入明文P是QUIC包的有效载荷，如{{QUIC-TRANSPORT}}中所述。

AEAD的输出密文C代替P发送。

一些AEAD功能限制了在相同的密钥和IV下可以加密多少个数据包（例如参见{{AEBounds}}）。
这可能低于数据包数量限制。在超过为正在使用的AEAD设置的任何限制之前，端点**必须**
启动密钥更新({{key-update}})。


## 包头保护(Header Protection) {#header-protect}

QUIC数据包报头的一部分，特别是数据包编号字段，使用与数据包保护密钥和IV分开导出
的密钥来保护。使用“quic hp”标签导出的密钥用于为那些不暴露于路径上元素的字段提供
机密性保护。

此保护适用于第一个字节的最低有效位以及数据包编号字段。对于具有长报头的数据包，
第一字节的四个最低有效位受到保护;第一个字节的五个最低有效位受到短标头数据包
的保护。对于两种报头形式，这包括保留位和分组号长度字段;对于具有短报头的数据
包，密钥相位位也受到保护。

在连接期间使用相同的报头保护密钥，密钥更新后值不会改变(参见{{key-update}})。
这允许使用报头保护来保护密钥阶段。

此过程不适用于重试或版本协商数据包，这些数据包不包含受保护的有效负载或此
过程保护的任何字段。


### 包头保护应用(Header Protection Application)

报头保护是在应用了数据包保护之后应用的(参见{{aead}})。分组的密文被采样并用作
加密算法的输入。所使用的算法取决于协商的AEAD。

此算法的输出是5字节掩码，该掩码使用异或应用于受保护的报头字段。分组的第一
字节的最低有效位被第一掩码字节的最低有效位屏蔽，并且分组编号用剩余字节屏蔽。
可能由较短的分组号编码产生的任何未使用的掩码字节都是未使用的。

{{pseudo-hp}} 显示了应用报头保护的示例算法。移除报头保护仅在确定分组编号长度
(Pn_Length)的顺序上不同。

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
{: #pseudo-hp title="报头保护伪码"}

{{fig-sample}} 显示了标有E的长标题和短标题的受保护字段。  {{fig-sample}} 还
显示了采样字段。

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
{: #fig-sample title="报头保护和密文样本"}

在TLS密码组可以与QUIC一起使用之前，必须为与该密码组一起使用的AEAD指定
报头保护算法。本文档定义了AEAD_AES_128_GCM, AEAD_AES_128_CCM,
AEAD_AES_256_GCM,AEAD_AES_256_CCM (所有AES AEAD在{{!AEAD=RFC5116}}中定义)
和AEAD_CHACHA20_POLY1305 {{!CHACHA=RFC8439}}的算法。在TLS选择密码组之前，
使用AES报头保护(({{hp-aes}})，匹配AEAD_AES_128_GCM数据包保护。

### 包头保护的示例（Header Protection Sample） {#hp-sample}

包头保护算法使用包头保护密钥和
数据包负载字段的一个抽样。

虽然每次都采样相同数量的字节，但还是要为了终端移能除保护做
一些工作，终端在移除保护时不知道包编号字段
的长度。在对密文进行采样时，假设
包编号字段长度位4字节（编码过后它的最大可能长度）。

终端 **必须** 丢弃哪些不足一个样本长度
的数据包。

为了确保在采样时有足够多的数据，数据包是扩展后的，所以
编码后的数据包的包编号字段和填充物的总长度，至少
比包头保护的采样过程要求的长4个字节。在{{?TLS13}}
定义的AEAD中，采用了16位扩展和16位
包头保护采样，这意味着如果包编号字段
被编码成单个字节，则至少需要帧中的3个字节
的填充物，如果被编码成2个字节，则需要帧中的2字节。

具有一个短包头的数据包的密文可以用如下伪码
采样（sample：样本）：

~~~
sample_offset = 1 + len(connection_id) + 4

sample = packet[sample_offset..sample_offset+sample_length]
~~~

比如，对于一个短包头的数据包，8为的连接ID，以及
使用AEAD_AES_128_GCM加密，采样选取第13到28个字节
（包含13和28，编号从0开始）。

对长包头的数据包采用相同的采样方式，注意同一UDP数据报可能
包含多个QUIC数据包，每个数据包都是
单独处理的。

~~~
sample_offset = 6 + len(destination_connection_id) +
                    len(source_connection_id) +
                    len(payload_length) + 4
if packet_type == Initial:
    sample_offset += len(token_length) +
                     len(token)

sample = packet[sample_offset..sample_offset+sample_length]
~~~


### AES包头保护（AES-Based Header Protection） {#hp-aes}

本部分定义使用AEAD_AES_128_GCM，AEAD_AES_128_CCM，
AEAD_AES_256_GCM和AEAD_AES_256_CCM进行包头保护的算法。AEAD_AES_128_GCM和
AEAD_AES_128_CCM使用128位AES{{!AES=DOI.10.6028/NIST.FIPS.197}}和
电子密码簿（ECB）模式。AEAD_AES_256_CCM和AEAD_256_CCM使用
256位AES和ECB模式。

这个算法采集密文的16字节。采样结果用作
算法的输入。伪代码如下：

~~~
mask = AES-ECB(hp_key, sample)
~~~


### ChaCha20包头保护（ChaCha20-Based Header Protection） {#hp-chacha}

当使用AEAD_CHACHA20_POLY1305的时候，包头保护使用在2.4章{{!CHACHA}}定义的
原始的ChaCha20函数。它使用256位的密钥和
16位密文采样。

密文采样结果的前4字节被解释为32位小端整数，
用来存储块数量。剩下的12位
被解释为3个连续的32位小端整数，
用来存放随机数。

通过使用5个0来调用ChaCha20来得到加密掩码。
伪代码如下：

~~~
counter = DecodeLE(sample[0..3])
nonce = DecodeLE(sample[4..7], sample[8..11], sample[12..15])
mask = ChaCha20(hp_key, counter, nonce, {0,0,0,0,0})
~~~


## 接收被保护的数据包（Receiving Protected Packets）

终端一旦成功的接收到一个有特定包编号的数据包之后，
终端**必须**丢弃那些在同一包编号空间中
无法被此密钥或下一个密钥 -如果密钥发生了更新-
（参见{{key-update}}）解密的更高编号的数据包。
类似的，试图更新密钥但无法
被成功解密的数据包**必须**被丢弃。

数据包解密失败并不意味着
对端存在协议错误或者攻击。QUIC使用的包编号截断方式
可能导致在数据包严重延迟的情况下无法被
正常解码。


## 使用0-RTT密钥（Use of 0-RTT Keys） {#using-early-data}

如果0-RTT密钥可用（参见{{enable-0rtt}}），则在缺乏重放保护的
情况下，有必要限制他们的使用来避免对协议发起的
重放攻击。

客户端**必须**仅使用0-RTT密钥来保护幂等的数据。客户端
**可能**想要对完成TLS握手前发送的数据
添加额外的限制。客户端要么把0-RTT密钥视为1-RTT密钥，否则
他**禁止**发送具有0-RTT密钥的ACK。

客户端在收到0-RTT数据被接受之后和在
收到完整的服务端握手消息之前，可以发送
0-RTT数据。客户端在收到0-RTT数据被拒绝的信息
之后**应该**停止发送0-RTT数据。

服务端**禁止**使用0-RTT密钥来保护数据包；服务端使用1-RTT密钥来
保护0-RTT数据包的确认信息。客户端**禁止**尝试去解密
他收到的0-RTT数据，反之**必须**丢弃他们。

注意：

: 服务端可以对0-RTT数据回复确认信息，但是
  任何包含0-RTT数据确认信息的数据包，都不应该
  让客户端在TLS握手完成前能够移除其保护。用来移除
  包保护的1-RTT密钥在客户端收到完整的
  握手消息之前不能被传输。


## 接收无需的保护后的帧（Receiving Out-of-Order Protected Frames） {#pre-hs-protected}

由于乱序和丢失，终端在接收TLS握手消息之前可能接收到
被保护的数据包。客户端可能无法解密服务端
发过来的1-RTT的数据包，但此时服务端又可以
解密客户端发送的1-RTT数据包。

然而，服务器在确认客户端完成握手，或
验证了预共享密钥
 -在这种情况下服务器选择使用预共享密钥-（参见4.2.11章{{!TLS13}}）
之前，**禁止**处理传入的1-RTT保护后的数据包。
验证这些信息可以让服务器确保ClientHello没有被修改过。被1-RTT密钥
保护的数据包**可能**被存储然后被解密并在握手完成
之后被使用。

服务器可能在收到ClientHello之前收到被0-RTT密钥保护
的数据包。服务器**可能**保留这个数据包以后再解密
并等待接受ClientHello。


# 密钥更新 {#key-update}
 一旦建立了1-RTT密钥并且正在使用短头部，就可以更新密钥。
 短头部中的KEY_PHASE位用于指示是否已发生密钥更新。
  KEY_PHASE位初始设置为0，然后在每次密钥更新时反转。

 KEY_PHASE位允许接收者检测密钥内容的变化，而不必接收触
 发变化的第一个数据包。注意到已更改的KEY_PHASE位的终端
 可以更新密钥并解密包含已更改位的数据包。

 此机制替换了TLS KeyUpdate消息。端点**禁止**发送TLS KeyUpdate
 消息。终端**必须**将TLS KeyUpdate消息的接收视为类型0x10a的连接
 错误，相当于unexpected_message的fatal级别TLS警报（参见{{tls-errors}}）。

　
终端**禁止**一次启动多个密钥更新。终端在收到并成功解密具有匹配KEY_PHASE的数据包之前，不能使用新密钥。

当KEY_PHASE位与预期不匹配时，接收端检测到密钥更新。它使用TLS提供的KDF
函数创建一个新密钥（参见TLS13]的第7.2节）和相应的读密钥和IV。头部
保护密钥不会被更新。

如果可以使用更新的密钥和IV对数据包进行解密和身份验证，则还会更新
终端用于数据包保护的密钥。然后，终端发送的下一个数据包将使用新密钥。

终端在检测到其对等方已更新密钥时并不总是需要发送数据包。
它发送的下一个数据包将只使用新密钥。如果终端在发送具有
更新密钥的任何数据包之前检测到第二次更新，则表示其对端
已更新密钥两次而不等待相互更新。终端**必须**将连续密钥更新
视为致命错误并中止连接。

端点**应该**保留旧密钥的时间不超过探测超时的三倍（PTO，
参见{{QUIC-RECOVERY}}）。在此期间之后，旧密钥及其相应的
密钥**应该**被丢弃。保留密钥允许终端处理使用旧密钥发送并在
网络中延迟的数据包。具有较高数据包编号的数据包始终使用更新的密
钥，并且**禁止**使用旧密钥进行解密。

这确保了一旦握手完成，具有相同KEY_PHASE的包体将具有相同的分组
保护密钥，除非在短时间的连续帧和重要分组重排序中存在多个密钥更新

~~~
   初始端　　　　　　　　　   　　              响应端

@M QUIC Frames
               New Keys -> @N
@N QUIC Frames
                      -------->
                                          QUIC Frames @M
                          New Keys -> @N
                                          QUIC Frames @N
                      <--------
~~~
{: #ex-key-update title="密钥更新"}

触发密钥更新的数据包可能在成功处理具有更高数据包编号
的数据包后到达。只有在存在密钥泄露和攻击时，或者如果
对端错误地恢复使用旧密钥，这才有可能。因为后者无法
与攻击分开来，所以如果终端检测到这种情况，它必须立
即终止连接。

在决定何时更新密钥时，终端**禁止**超过使用特定密钥的限制，
如{{!TLS13}}的第5.5节所述。


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

## 对端拒绝服务（Peer Denial of Service） {#useless}

QUIC、TLS和HTTP/2都包含在某些上下文中具有合法用途的消息，
但是这些消息可能被滥用，导致对端花费处理资源，而不会对连接状态产生任何可见的影响。
如果处理与可观察到的带宽或状态影响相比异常大，
那么这可能允许恶意对端耗尽处理能力而不产生后果不被察觉。

QUIC禁止发送空`STREAM`帧，除非它们被标记为FIN位。
这可以防止只会浪费精力的`STREAM`帧被发送。

虽然某些冗余包有合法的用途，但是实现**应该**跟踪冗余包，
并将任何非生产性包的过量数量视为攻击的指示。


## 报头保护分析（Header Protection Analysis） {#header-protect-analysis}

报头保护依赖于包保护AEAD是伪随机函数(PRF)，而这不是AEAD算法所保证的属性。
因此，不能在一般情况下对这一机制的一般安全作出强有力的保证。
本文中描述的AEAD算法假设为PRFs。

本文档定义的包头保护算法采用以下形式:

~~~
受保护的字段（protected_field） = 字段 XOR 伪随机算法（PRF） (hp_key, sample)
~~~

这种结构对选择明文攻击是安全的(IND-CPA) {{IMC}}。

多次使用相同的密钥和密文样本可能会损害报头保护。
使用相同的密钥和密文示例保护两个不同的报头，可以显示受保护字段的排他性或。
假设AEAD作为PRF，如果采样L位，两个密文样本相同的概率接近2^(-L/2)，即生日界。
对于本文描述的算法，这个概率是2^64分之一。

注意:

: 在某些情况下，可以使用小于包保护算法所需的完整大小的输入。

为了防止攻击者修改包报头，使用包保护对包报头进行瞬时身份验证;
整个包报头是经过身份验证的附加数据的一部分。
被伪造或修改的受保护字段只有在删除包保护之后才能检测到。

攻击者可以猜测包号的值，并通过定时侧通道进行终端确认猜测。
类似地，可以测试和公开数据包长度的猜测。
如果数据包的接收者丢弃了具有重复数据包号的数据包，而没有试图删除数据包保护，
那么他们可以通过定时侧通道显示数据包号与接收到的数据包匹配。
为了使认证不受侧通道的影响，**必须**同时应用报头保护移除、包号恢复和包保护移除的整个过程，
而不需要定时和其他侧通道。

对于包的发送，包有效载荷和包号的构造和保护**必须**不受侧通道的影响，
侧通道会显示包号或其编码大小。


## 密钥的多样性 (Key Diversity)

在使用TLS时，使用了TLS的中心密钥调度。
由于将TLS握手消息集成到机密计算中，包含QUIC传输参数扩展可以确保握手和1-RTT密钥
与在TCP上运行TLS的服务器可能生成的密钥不同。
为了避免跨协议密钥同步的可能性，还提供了其他措施来改进密钥分离。

与TLS中的等效密钥不同，QUIC包保护密钥和IVs是使用不同的标签派生的。

为了保持这种分离，新版本的QUIC**应该**为包保护密钥和IV的密钥派生定义新的标签，
以及报头保护密钥。这个版本的QUIC使用字符串“quic”。
其他版本可以使用特定于版本的标签来替代该字符串。

最初的秘密使用的密钥是特定于协商好的QUIC版本。
新的QUIC版本**应该**定义一个新的随机混淆值，用于计算初始秘密。


# IANA的考虑 （IANA Considerations）
本文档不创建任何新的IANA注册表，但在以下注册表中注册值:

* TLS ExtensionsType Registry {{!TLS-REGISTRIES=RFC8447}} -
  IANA用于注册 {{quic_parameters}}中找到的quic_transport_parameters扩展。
  建议将列标记为Yes。TLS 1.3列包括CH和EE。

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
