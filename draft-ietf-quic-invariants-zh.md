---
title: "Version-Independent Properties of QUIC"
abbrev: QUIC Invariants
docname: draft-ietf-quic-invariants-latest
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
        org: Google
        role: editor
      -
        ins: M. Thomson
        name: Martin Thomson
        org: Mozilla
        role: editor

informative:

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


--- abstract

这篇文档描述了 QUIC 传输协议的一些特性，这些特性
预计会在以后的新版本协议中
保持不变。


--- note_Note_to_Readers

关于次草案的相关讨论在QUIC工作组邮件列表（quic@ietf.org）
中进行，邮件列表的归档存放在
<https://mailarchive.ietf.org/arch/search/?email_list=quic>.

工作组的信息可以在<https://github.com/quicwg>中找到，此文档的
源代码和问题列表在
<https://github.com/quicwg/base-drafts/labels/-invariants>.


--- middle

# 简介（Introduction）

为了提供安全的，多路复用的传输 QUIC {{QUIC-TRANSPORT}} 包含
版本协商的能力。这允许协议随着时间的推移可以改变以
应对新的需求。这个协议的很多特性会随版本
而改变。

这篇文档描述了 QUIC 的一个子集，此子集在新版本的
开发和部署当中保持不变。所有的这些不变性
都和IP版本无关。

此文档的主要目标在于保证部署新
版本的 QUIC 是可能的。本文档通过记录不可变特性的方式，
来确保更改协议其他部分
的能力。因此，除了本文档中提到的部分，协议
的任何部分都能因版本不同而不同。

在 {{bad-assumptions}} 当中列举了一些错误的假设，这些
假设可能基于第一版的 QUIC，但他们并不适用于所有
版本的 QUIC。


# 约定和定义（Conventions and Definitions）

关键词 “**必须(MUST)**”，“**禁止(MUST NOT)**”，“**必需(REQUIRED)**”，
“**应当(SHALL)**”，“**应当不(SHALL NOT)**”，“**应该(SHOULD)**”，
“**不应该(SHOULD NOT)**”，“**推荐(RECOMMENDED)**”，“**不推荐(NOT RECOMMENDED)**”，
“**可以(MAY)**”，“**可选(OPTIONAL)**” 在这篇文档中
将会如 BCP 14 {{!RFC2119}}{{!RFC8174}} 中描述的，
当且仅当他们如此例子显示的以加粗的形式出现时。

此文档使用 {{QUIC-TRANSPORT}} 当中描述的术语和符号约定。


# 对 QUIC 极其抽象的描述（An Extremely Abstract Description of QUIC）

QUIC 是一个面向连接的端到端协议。端之间
交换 UDP 数据报。被传输的 UDP 数据报包含 QUIC 数据包。QUIC 终端
使用 QUIC 数据包来建立 QUIC 连接，QUIC 连接两端的终端是共享
连接状态的。


# QUIC 数据包头（QUIC Packet Headers）

QUIC 数据包是在 QUIC 终端之间交换的 UDP 数据报的内容。
此文档描述这些数据报的内容。

QUIC 定义了两种包头：长包头和短包头。第一个字节
的最高有效位被设置意味着它是一个长包头包；
否则为短包头包。

除了此处描述的值，QUIC 的载荷部分是
版本特定的，并且长度不固定。


## 长包头（Long Header）

长包头的格式在 {{fig-long}} 当中描述。具有版本特定
含义的位以 X 标记。

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|1|X X X X X X X|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Version (32)                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|DCIL(4)|SCIL(4)|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|               Destination Connection ID (0/32..144)         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                 Source Connection ID (0/32..144)            ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|X X X X X X X X X X X X X X X X X X X X X X X X X X X X X X  ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #fig-long title="QUIC 长包头"}

拥有长包头的 QUIC 数据包，其第一个字节的首位会被设置为1。
此字节的其他位是版本特定的。

接下来的4字节包含一个32位的版本字段（参见 {{version}}）。

接下来的一位描述之后的两个连接 ID 的
字节数（参见 {{connection-id}}）。每个长度都被编码位4位
无符号整数。此字节的高4位为目标连接 ID 的长度（DCIL），低
4位为源连接 ID 的长度（SCIL）。
如果长度为0，则代表着连接 ID 也
为0字节长。非0的数字需要被加上3
以得到最终的连接 ID 长度；因此最终的长度
会是0或者4到18位之间的数（包括18）。例如，0xe0这个
字节代表着17个字节的目标连接 ID 和0字节的
源 ID。

连接 ID 长度字段之后紧接着是两个连接 ID。与数据包接收者
关联的连接 ID（目标连接 ID）首先出现，接着是于数据包发送
者关联的 ID（
源连接 ID）。

数据包剩下的部分是版本特定的内容。


## 短包头（Short Header）

短包头的格式在 {{fig-short}} 当中描述。具有版本特定
含义的位以 X 标记。

~~~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|0|X X X X X X X|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                 Destination Connection ID (*)               ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|X X X X X X X X X X X X X X X X X X X X X X X X X X X X X X  ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~~~
{: #fig-short title="QUIC 短包头"}

短包头的 QUIC 数据包，其第一字节的首位被设置为0。

短包头的 QUIC 数据包包含一个目标连接 ID。短包头
不包含连接 ID 长度字段，源连接 ID 字段，以及
版本字段。

数据包剩下的部分的语意为版本特定的。


## 连接ID（Connection ID） {#connection-id}

连接 ID 是一个有任意长度的不透明字段。

连接 ID 的主要作用是保证在底层协议（UDP，IP，或更底层）
的寻址方式改变时，QUIC 数据包不会
被传送到错误的终端。终端和支持的媒介
会使用连接 ID 来确保每个 QUIC 包
都能被分发到正确的终端。在终端，连接 ID 被
用来区分数据包是来自于
哪个 QUIC 连接的。

连接 ID 是每个终端使用版本特定的方法选择的。
来自同一个 QUIC 连接的数据包可能使用不同的连接 ID 值。


## 版本（Version）

QUIC 使用32为整数来标记版本，该整数以网络序
编码。版本0是为版本协商预留的（参见 {{version-negotiation}}）。
任何其他值都可被用作版本号。

此文档描述的特性适用于所有版本的 QUIC。不符合
此文档中描述的特性的协议
不是 QUIC。今后的文档可能描述特定
版本 QUIC 的额外特性，或对一定版本 QUIC 适用的特性。

# 版本协商（Version Negotiation） {#version-negotiation}

当一个 QUIC 终端收到一个长包头的包，并且此包使用的
协议版本它不支持，则可能在响应当中
发送版本协商包。短包头包不会触发
版本协商。

版本协商包的第一个字节的首位会被设置，因此
它符合在 {{long-header}} 当中定义的长包头数据包
格式。版本协商包的版本号字段会被
设置为0x00000000，可以以此来判断是否为版本协商包。

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|1|X X X X X X X|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Version (32) = 0                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|DCIL(4)|SCIL(4)|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|               Destination Connection ID (0/32..144)         ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                 Source Connection ID (0/32..144)            ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Supported Version 1 (32)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   [Supported Version 2 (32)]                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
                               ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   [Supported Version N (32)]                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #version-negotiation-format title="版本协商包"}


版本协商包包含一连串支持的版本字段，每一个字段
都代表一个被发送此包的终端所支持的版本。受
支持版本字段是紧接着版本字段的。版本协商包
不包含其他的额外字段。终端**必须**忽略
那些没有支持版本字段或支持版本字段被截断的包。

版本协商包不使用完整性保护和加密保护。
特定版本的 QUIC 可能会在连接建立的过程中
对数据包进行认证。

终端**必须**将其收到的数据包的源连接 ID 字段的值
包含近目标连接 ID 字段。源连接 ID 字段必须是从
收到的包的目标连接 ID 字段复制过来的，此 ID 最初
由客户端随机选择。通过回显两个
连接 ID 的方式，可以确切的告诉客户端服务器收到了数据包
并且版本协商包不是由路径外攻击者
生成的。

收到版本协商包的终端可能将后续数据包
使用的协议版本变更为自己选择的版本。终端
更改 QUIC 版本需要满足的条件是取决于它
所选择的 QUIC 版本的。

想要了解支持 QUIC 版本1的终端是如何生成和使用
版本协商包的，请参考 {{QUIC-TRANSPORT}}。


# 安全和隐私注意事项（Security and Privacy Considerations）

中间设备可能会用到某些版本的 QUIC 协议所特有的特性，
并假设其他版本的 QUIC 表现出相同的特征时，具有相同
的语意。这种特性可能会很多（参见 {{bad-assumptions}}）。
已经在消除或掩盖 QUIC 版本1的可观察特性方面做了
很多工作，但仍然还有很多。
其他版本的 QUIC 可能出于不同的设计考虑表现出
不同的特性。

QUIC 的版本号并不会存在于所有的数据包当中，这意味着
中间设备想要基于特定版本的特性从流中可靠的提取信息时，
需要保留每个连接 ID 的状态。

此文档当中描述的版本协商包是没有
完整性保护的；它仅有用来防止路径外攻击者插入版本协商包的简单保护。
每个 QUIC 版本都**必须**定义对版本协商包中的值进行认证的机制。


# IANA 注意事项（IANA Considerations）

本文档没有 IANA 相关的事项。


--- back

# 不正确的假设（Incorrect Assumptions） {#bad-assumptions}

QUIC 版本1 {{QUIC-TRANSPORT}} 当中有很多特性是观察者可见的，
但在部署新版本的时候仍应被
视为可变的。

本章节列举了一些基于版本1的 QUIC 可能会得出的
错误假设。有些假设甚至在版本1的 QUIC 当中也是
错的。此列表并不没有穷尽所有的问题，它只是
举一些例子。

下列描述在所有版本的 QUIC 当中都**不**正确：

* QUIC 使用 TLS {{QUIC-TLS}} 并且一些TLS信息在路径上是可见的

* 长包头 QUIC 包只会在连接建立的过程中被使用

* 在一个给定的5元组重的所有连接都会有连接建立过程

* 流当中第一个被交换的包使用长包头

* QUIC 禁止确认仅包含 ACK 帧的数据包，因此可以
  假定在长时间静默之前的最后一个数据包
  包含确认。

* QUIC 在连接建立的时候使用 AEAD（AEAD_AES_128_GCM {{?RFC5116}}）
  来保护数据包。

* QUIC 数据包编号紧接着版本字段。

* QUIC 数据包编号每发送一个数据包就增加1。

* QUIC 规定了客户端发送的第一个我手包的最小大小

* QUIC 规定由客户端发起会话

* 只有服务器会发送 QUIC 版本协商包

* QUIC 的连接 ID 不经常变化

* QUIC 终端会在发送版本协商包之后改变其使用的
  协议版本。

* QUIC 长包头中的版本字段在两个方向上是一样的

* 一对终端之间一次只会建立
  一个 QUIC 连接
