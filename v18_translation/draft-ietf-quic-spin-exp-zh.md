---
title: QUIC延迟自旋位（The QUIC Latency Spin Bit）
abbrev: QUIC Spin Bit
docname: draft-ietf-quic-spin-exp-latest
date: {DATE}
category: std

ipr: trust200902
workgroup: QUIC
keyword: Internet-Draft

stand_alone: yes
pi: [toc, sortrefs, symrefs]

author:
  -
    ins: B. Trammell
    role: editor
    name: Brian Trammell
    org: ETH Zurich
    email: ietf@trammell.ch
  -
    ins: M. Kuehlewind
    name: Mirja Kuehlewind
    org: ETH Zurich
    email: mirja.kuehlewind@tik.ee.ethz.ch

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

informative:
  CACM-TCP:
    title: Passively Measuring TCP Round-Trip Times (in Communications of the ACM)
    author:
      -
        ins: S. Strowes
    date: 2013-10
  TMA-QOF:
    title: Inline Data Integrity Signals for Passive Measurement (in Proc. TMA 2014)
    author:
      -
        ins: B. Trammell
      -
        ins: D. Gugelmann
      -
        ins: N. Brownlee
    date: 2014-04
  PAM-RTT:
    title: Revisiting the Privacy Implications of Two-Way Internet Latency Data (in Proc. PAM 2018)
    author:
      -
        ins: B. Trammell
      -
        ins: M. Kuehlewind
    date: 2018-03

--- abstract

这篇文档详细说明了QUIC传输协议的一个额外的
延迟自旋位，并描述了如何使用它来测量端对端的延迟。


--- note_Note_to_Readers

这篇文档详细说明了QUIC传输协议的一个试验性增强。
具体地说，这个实验目的在于确定：

- 增加自旋延迟位对实现的影响，以及会对规范增加
  多少复杂度；以及
- 在实时的网络传输中自旋位测量结果的导出值以及其准确性。

这个实验产生的数据将会被QUIC工作组用来
决定延迟自旋位的
标准。尽管这是一个工作组文档，但它现在还**不能**
被交付。

关于次草案的相关讨论在QUIC工作组邮件列表（quic@ietf.org）
中进行，邮件列表的归档存放在
<https://mailarchive.ietf.org/arch/search/?email_list=quic>.

工作组的信息可以在<https://github.com/quicwg>中找到，此文档的
源代码和问题列表在
<https://github.com/quicwg/base-drafts/labels/-spin>.


--- middle

# 简介（Introduction）

QUIC协议内部{{QUIC-TRANSPORT}}大部分使用
传输层传输层安全（TLS）{{?TLS=RFC8446}}
来加密。与TCP不同的是，QUIC不像TCP那样给路径上的观察者
暴露可以用于端到端延迟的序列号、确认号以及时间戳
（如果这些字段是确认使用的）。
目前QUIC的链路镜像（参见{{?WIRE-IMAGE=I-D.trammell-wire-image}}）不
暴露任何延迟测试技术（例如{{CACM-TCP}}，{{TMA-QOF}}}）
所需要的信息。

此文档在QUIC的短头增加了一个明确的信号“自旋位”
来增加被动延迟测试的能力。
被动的观察者通过对自旋位的被动观察可以得到每个RTT
一个的RTT样本。此文档介绍了它是如何被增加到QUIC
当中，以及它是如何被用到被动测量设施中来生成RTT样本
的。


# 自旋位的原理（The Spin Bit Mechanism）

延迟自旋位允许网络路径上的观察点在连接期间
检测延迟。由于测量握手RTT不需要
自旋位，因此在短包头当中增加自旋位
就足够了。因此自旋位仅仅会在
版本商谈和连接建立之后才会出现。

## 包含自旋位的包头的建议格式（Proposed Short Header Format Including Spin Bit） {#header}

{{QUIC-TRANSPORT}}指定使用第短包头的第一个字节的
第三个最高有效位来做自旋位（0x20，在{{fig-short-header}}当中
标记为S）。自旋位取值为0或1，取决于其存储的自旋值，自旋值在包
被接受的时候更新，就像在{{spinbit}}中描述的那样。

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
{: #fig-short-header title="短包头格式"}

## 在发出的包中增加自旋位（Setting the Spin Bit on Outgoing Packets） {#spinbit}

终端，客户端和服务端，对每一个QUIT连接维持一个自旋值，0或1，
在发送短包头的包时，将包头的自旋位设置成
当前存储的值。自旋值在连接开始时在
任何终端都初始化为0，无论客户端还是服务端。
每个终端同样记录着从单个连接当中看到的对端
发送的最大的包编号。

接着，在一个单个连接当中每个终端以如下步骤确定
自旋值：

* 当服务端收到一个客户端发来的包时，如果此包有
  一个短包头，并且它的包编号比服务端已知的从客户端发来的
  最大包编号大，服务端将自旋值设置为从此包的自旋位
  中观察到的值。

# 当客户端收到一个服务端发来的包时，如果此包有一个短
  包头，并且它的包编号比客户端已知的从服务端发来的最大
  包编号大，客户端将自旋值设置为从此包的自旋位中
  观察到的值的相反值。

上述过程会导致自旋位在每个方向上，一次往返改变一次
值。观察点可以通过观察延迟自旋位的这种改变
来估计网络的延迟，就像{{usage}}当中描述的一样。
参考{{?QUIC-SPIN=I-D.trammell-quic-spin}}中的更过图表
来理解这个过程的原理。

## 重设自旋位状态（Resetting Spin Value State） {#state-reset}

每一个客户端和服务端都在发送每个具有新连接ID的连接
的第一个包时，重设它的自旋值为0。这降低了
利用自旋位瞬间的状态跨连接链接流迁移以及
ID改变的风险。

# 在RTT被动测量中使用自旋位（Using the Spin Bit for Passive RTT Measurement） {#usage}

当一个QUIC流连续发送数据时，在每个方向上自旋延迟位的值
每隔一个往返时间（RTT）变更一次。一个路径上的观察者
可以通过观察单方向上自旋位信号边缘（从0到1或从1到0）间
的时差，来测量端到端RTT的一个
样本。

注意这种测量方式，就如TCP的被动RTT测量一样，包含
任何传输协议延迟（例如，延迟发送确认包），
和/或应用层延迟（例如等待请求完成）。
因此它给路径上的设备提供了一个很好的估计
应用程序感知到的瞬时RTT的方法。可以使用简单的线性平滑或者移动最小滤波器
在RTT流上，来得到更稳定的
预测结果。

然而，被应用程序限制的或被流量控制限制的发送方会具有
应用延迟和传输延迟，他们各自都比网络RTT
高很多。当发送方被应用程序限制时，例如仅
发送少量周期性的应用数据且此周期大于RTT的时候，
测量自旋位得到的信息会是应用程序
的周期而不是网络RTT。

基于每个流上观察到的数据速率或RTT序列中的变化的
简单启发算法，可以被用来过滤由于丢失和乱序的自旋信号所带来的
错误RTT样本，也可以用作过滤应用或流量控制的限制。例如，
QoF{{TMA-QOF}}拒绝组件的RTT明显高于流上
历史RTT。这些启发算法可能会使用握手RTT作为
一个给定流的RTT的初始估计值。

一个可以观察到两个方向上的传输数据的路径上的观察者（从客户端
到服务端以及从服务端到客户端）可以使用自旋位来测量
“上游”和“下游”部分的RTT。也就是说，端到端RTT可以归结到
观察者服务端的路径和观察者到客户端的路径。它通过测量
在上游方向上观察到的自旋边缘以及下游方向上观察到的自旋边缘间
的延迟来实现，反之亦然。

# 禁用自旋位（Disabling the Spin Bit）

实习**应该**允许客户端和服务器的管理者从
全局或单连接角度去禁用自旋位。
即使管理员没有禁用自旋位，实现也**应该**
在连接的随机选择部分
禁用自旋位。

设计选择程序的时候**应该**认为
网络中平均有1/8的路径是禁用自旋位的。
选择程序**应该**是不能被外部预测的，
但对于给定的源地址/端口和目标地址/端口的组合是固定的。例如，
实现可能会用一个固定的值当作一个伪随机函数的种子，
并用此函数的输出来决定是否
发送自旋位。连接开始时的选择过程
**应该**在连接使用的所有路径上都执行。

注意在多个连接使用相同路径的时候，
自旋位的使用**可能**会被终端调整，
注意一下这在很多时候可能是不可能的。

当自旋位被禁用的时候，终端**可能**将自旋位设置成任何值，
并且终端**必须**接受任何传入的值。**建议**将自旋位
设置成一个随机值，可以是每个包独立决定，
也可以是每个路径独立决定一次。

# IANA兼容（IANA Considerations）

此文档没有考虑IANA。

# Security and Privacy Considerations

The spin bit is intended to expose end-to-end RTT to observers along the path,
so the privacy considerations for the latency spin bit are essentially the
same as those for passive RTT measurement in general. It has been shown
{{PAM-RTT}} that RTT measurements do not provide more information for
geolocation than is available in the most basic, freely-available IP address
based location databases. The risk of exposure of per-flow network RTT to
on-path devices is in most cases negligible.

There is however an exception, when parts of the path from client to server
are hidden from observers. An example would be a server accessed through a
proxy. The spin bit allows for measurement of the end-to-end
RTT, and will thus enable adversaries near the endpoint to discover that
the connection does not terminate at the visible destination address.

Endpoints that want to hide their use of a proxy or a relay will want to
disable the spin bit. However, if only privacy-sensitive clients or servers ever
disabled the spin bit, they would stick out. The probabilistic disabling
behavior explained in {{disabling-the-spin-bit}} ensures that other endpoints
will also disable the spin bit some of the time, thus hiding the
privacy sensitive endpoints in a large anonymity set. It also provides
for a minimal greasing of the spin bit, in order to mitigate risks of
ossification.


# Change Log

> **RFC Editor's Note:**  Please remove this section prior to
> publication of a final version of this document.

## Since draft-ietf-spin-exp-00

Adding section on disabling the spin bit and privacy considerations.

# Acknowledgments
{:numbered="false"}

This document is derived from {{QUIC-SPIN}}, which was the work
of the following authors in addition to the editor of this document:

- Piet De Vaere, ETH Zurich
- Roni Even, Huawei
- Giuseppe Fioccola, Telecom Italia
- Thomas Fossati, Nokia
- Marcus Ihlar, Ericsson
- Al Morton, AT&T Labs
- Emile Stephan, Orange

The QUIC Spin Bit was originally specified in a slightly different form by
Christian Huitema.

This work is partially supported by the European Commission under Horizon 2020
grant agreement no. 688421 Measurement and Architecture for a Middleboxed
Internet (MAMI), and by the Swiss State Secretariat for Education, Research,
and Innovation under contract no. 15.0268. This support does not imply
endorsement.

--- back
