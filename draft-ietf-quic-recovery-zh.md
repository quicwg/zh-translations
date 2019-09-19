---
title: QUIC Loss Detection and Congestion Control
abbrev: QUIC Loss Detection
docname: draft-ietf-quic-recovery-latest
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
    ins: I. Swett
    name: Ian Swett
    org: Google
    email: ianswett@google.com
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

  QUIC-TLS:
    title: "Using TLS to Secure QUIC"
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

  FACK:
    title: "Forward Acknowledgement: Refining TCP Congestion Control"
    author:
      - ins: M. Mathis
      - ins: J. Mahdavi
    date: 1996-08
    seriesinfo: ACM SIGCOMM

--- abstract

This document describes loss detection and congestion control mechanisms for
QUIC.

--- note_Note_to_Readers

Discussion of this draft takes place on the QUIC working group mailing list
(quic@ietf.org), which is archived at
<https://mailarchive.ietf.org/arch/search/?email_list=quic>.

Working Group information can be found at <https://github.com/quicwg>; source
code and issues list for this draft can be found at
<https://github.com/quicwg/base-drafts/labels/-recovery>.

--- middle

# 简介

QUIC是一种新的基于UDP的多路复用和安全传输。QUIC建立在数十年的运输
和安全经验的基础上，并实现了使其作为具有吸引力的现代通用运输的机制。
{{QUIC-TRANSPORT}中介绍了QUIC协议。

QUIC实现了现有TCP丢失恢复机制的精神，在RFC、各种Internet草稿以及
Linux TCP实现中都有描述。本文档描述了QUIC拥塞控制和丢失恢复，并
在适用的情况下，其TCP等价属性等同于RFC、Internet草稿、学术论文和
/或TCP实现。


# 约定和定义

关键词 **“必须(MUST)”**， **“禁止(MUST NOT)”**， **“必需(REQUIRED)”**，
**“应当(SHALL)”**， **“应当不(SHALL NOT)”**， **“应该(SHOULD)”**，
**“不应该(SHOULD NOT)”**， **“推荐(RECOMMENDED)”**，
**“不推荐(NOT RECOMMENDED)”**， **“可以(MAY)”**， **“可选(OPTIONAL)”**
在这篇文档中将会如 BCP 14 [`RFC2119`] [`RFC8174`] 中描述的， 当且仅当
他们如此例子显示的以加粗的形式出现时。 文档中使用的术语在下方描述。

本文档中使用的术语定义：

仅有ACK（ACK-only）:

: 仅包含一个或多个ACK帧的任何数据包。

传输中（In-flight）:

: 如果数据包已发送，且既未确认也未声明丢失，则视为传输中的数据包，
  并且它们不是仅有ACK的包。

ACK引出帧（Ack-eliciting Frames）:

: 除ACK或PADDING之外的所有帧都被认为是ACK引出帧。

ACK引出包（Ack-eliciting Packets）:

: 包含ACK引出帧且在最大ACK延迟内从接收器引出ACK的数据包，称为ACK引出数据包。

加密数据包（Crypto Packets）:

: 包含在初始或握手数据包中发送的加密数据的数据包。

无序数据包（Out-of-order Packets）:

: 不会使其包数空间的最大接收包数增加1的包。当早期的数据包丢失或延迟时，
  数据包将无序到达。

# QUIC传输机制的设计

QUIC中的所有传输都使用数据包级报头发送，该报头指示加密级别，并包括数据
包序列号(以下称为数据包号)。如{{QUIC-TRANSPORT}}中所述，加密级别表示
数据包编号空间。在连接的生存期内，数据包号在数据包号空间内永远不会重复。
包编号在空间内单调增加，防止歧义。

这种设计避免了在传输和重新传输之间消除歧义的需要，并消除了QUIC对TCP
丢失检测机制的解释的显著复杂性。

QUIC数据包可以包含多个不同类型的帧。恢复机制确保需要可靠传输的数据和
帧被确认或声明丢失，并在必要时在新的数据包中发送。数据包中包含的帧类型
会影响恢复和拥塞控制逻辑：

* 所有包都被确认，尽管不包含ACK引出帧的包仅与ACK引出包一起被确认。

* 包含加密帧的长报头数据包对于QUIC握手的性能至关重要，并使用较短的计时
  器进行确认和重新传输。

* 仅包含ACK帧的数据包不会计入拥塞控制限制，也不会被视为传输中的数据包。

* PADDING帧会导致数据包对传输中的字节做出贡献，而不会直接导致发送确认。

## QUIC和TCP之间的相关差异

熟悉TCP的丢失检测和拥塞控制的读者将在这里找到与众所周知的TCP算法并行的
算法。然而，QUIC和TCP之间的协议差异会导致算法差异。我们将在下面简要描述
这些协议差异。

### 单独的数据包号空间

QUIC对每个加密级别使用单独的包号空间，除了0-RTT和所有代的1-RTT密钥使用
相同的包号空间。单独的包号空间确保用一个加密级别发送的包的确认不会导致用
不同加密级别发送的分包的虚假重传。拥塞控制和往返时间(RTT)测量是跨包号空
间统一的。

### 单调递增数据包数

TCP将发送方的传输顺序与接收方的传递顺序合并在一起，这会导致承载相同序列
号的相同数据的重传，从而导致“重传歧义”。QUIC将两者分开：QUIC使用数据包号
来指示传输顺序，并且任何应用程序数据都在一个或多个流中发送，传递顺序由STREAM帧
中编码的流偏移确定。

QUIC的包号在包号空间内严格递增，并直接编码传输顺序。较高的数据包编号表示该
数据包是较晚发送的，而较低的数据包编号表示该数据包是较早发送的。当检测到包含
ACK引出帧的数据包丢失时，QUIC会将必要的帧重新绑定到具有新数据包号的新数据包中，
从而消除接收到ACK时确认哪个数据包的模糊性。因此，可以进行更精确的RTT测量，
检测到虚假的重发，并且可以仅仅基于分组编号来普遍应用诸如快速重发的机制。

这个设计点大大简化了QUIC的丢失检测机制。大多数TCP机制都会隐式地尝试根据TCP序列
号推断传输顺序-这是一项非常重要的任务，特别是当TCP时间戳不可用时。

### 更清晰的丢失时期

当声明丢失后发送的数据包被确认时，QUIC结束丢失时期。TCP等待序列号空间中的间隙被填满，
因此，如果一个段在一行中丢失多次，丢失的时间可能不会在几个往返过程中结束。因为这两种
方法都应该每一个时期只减少一次拥塞窗口，所以对于每一个遭受损失的往返行程，QUIC将正确
地进行一次，而TCP可能只在多个往返行程中进行一次。

### 不准食言

QUIC ACK包含类似于TCP SACK的信息，但QUIC不允许确认数据包后再拒绝，
从而极大地简化了双方的实现，并降低了发送方的内存压力。

### More ACK Ranges

QUIC supports many ACK ranges, opposed to TCP's 3 SACK ranges.  In high loss
environments, this speeds recovery, reduces spurious retransmits, and ensures
forward progress without relying on timeouts.

### 延迟ACK的显式矫正

QUIC 将从接收端收到包到发出 ACK 之间的
延迟显式的编码在 ACK 包中。这样 ACK 包的
接收者（译注：即发包方）可以在估计 RTT 的时候调整
接收方延迟，尤其是延迟 ACK 的定时器。这项机制还允许接收者
测量及报告从 OS 内核接收到数据包开始的延迟，
这在一个可能导致延迟的接收着中很有用，例如
在一个在用户空间的 QUIC 接收者在处理接收到的包之前的上下文切换延迟。

# 生成确认

QUIC**应该**延迟发送
响应数据包的确认，但**禁止**
过于延迟确认需要ack的数据包。
特别的，
实现**必须**强制执行最大确认延迟，
以避免导致对端虚假超时。
最大ACK延迟在`max_ack_delay`传输参数
中传递，默认值为25ms。

**应该**在接收到第二个
ACK引出分组后立即发送确认。
QUIC恢复算法不假设对端在
接收到第二个ack引出分组时
立即发送ACK。

为了加快丢失恢复并减少超时，
接收方**应该**在收到无序数据包
后立即发送ACK。
它在收到乱序分组后到
发送立即ACK的时间**禁止**超过1/8 RTT，
除非更多乱序分组到达。
如果每个数据包都无序到达，
则应为每个接收到的数据包发送立即ACK。

同样，在IP报头中标记有ECN拥塞经历(CE)
代码点的数据包**应该**立即得到确认，
以减少对端对拥塞事件的响应时间。

作为优化，接收器**可以**在发送
任何ACK帧作为响应之前处理多个分组。
在这种情况下，接收器可以确定在
处理传入分组之后应该生成立即确认
还是延迟确认。

## 加密握手数据

为了快速完成握手并避免
由于密码重传超时而导致的
虚假重传，密码分组的发送**应该**
使用非常短的ACK延迟，
例如本地计时器粒度。
当密码栈指示已经接收到
该分组编号空间的所有数据时，
**可以**立即发送ACK帧。

## ACK范围

当发送ACK帧时，
可以包括一个或多个数据包的确认。
包括较旧的分组的确认，
这降低了由于丢失先前发送的
ACK帧而导致的虚假重传的机会，
但代价是较大的ACK帧。

ACK帧**应该**始终
确认最近接收到的数据包，
并且数据包越乱序，就越需要
快速发送更新的ACK帧，
以防止对端宣布数据包丢失
并突发地重新传输它包含的帧。

以下是一种用于确定ACK帧中
包含哪些数据包的推荐方法。

## 接受者追踪ACK帧

当发送包含ACK帧的数据包时，
可以保存在该帧中确认的最大值。
当确认包含ACK帧的数据包时，
接收方可以停止确认小于或
等于发送的ACK帧中已确认的
最大值的数据包。

在没有ACK帧丢失的情况下，
此算法允许最小1RTT的重新排序。
在ACK帧丢失和重新排序的情况下，
此方法不能保证发送方在确认
不再包含在ACK帧中前看到
每个确认。分组可能被无序接收，
并且包含它们的所有后续ACK帧都
可能丢失。
在这种情况下，
丢失恢复算法可能会
导致虚假重传，但发送方将
继续向前处理。

# 计算RTT估计值

当ACK帧到达时计算
往返时间(RTT)。
计算当前时间和发送
最大确认数据包的
时间之间的差值。
**禁止**对未被新确认
或未进行ACK-LEICING的
数据包采取RTT样本。

计算RTT时，来自ACK帧的
ACK延迟范围**应该**限制
为对端指定的max_ack_delay。
将ack_delay限制为max_ack_delay
可确保指定极小的max_ack_delay的
对端不会比正确指定max_ack_delay的
对端造成更多虚假超时。
只要结果大于min_RTT，
就**应该**从RTT中减去它。
如果结果小于MIN_RTT，
则应使用RTT，但应忽略ACK
延迟范围。

发送方计算平滑RTT(SRTT)和
RTT方差(RTTVAR)的方法与
{{?RFC6298}}中指定的类似，
参见{{on-ack-received}}。

当接收到确认比之前更大的
数据包编号的ACK帧时，
发送方获取RTT样本
(参见{{on-ack-received}})。
当在RTT内接收到多个这样的ACK帧时，
发送方将在每个RTT中获取多个RTT样本。
当在一个RTT内生成多个样本时，
平滑的RTT和RTT方差可能会
保留不充分的历史记录，
如{{?RFC6298}}中所建议的。
改变这些计算目前是一个开放的
研究问题。

MIN_RTT是在按ACK延迟
进行调整之前通过连接测量的
最小RTT。
忽略MIN RTT的
ACK延迟可防止有意或
无意低估MIN RTT，
进而防止低估平滑的RTT。


# 丢包检测 {#loss-detection}

QUIC发送器使用ACK信息和
超时来检测丢失的数据包，
本节介绍了这些算法。

如果数据包丢失，
QUIC传输需要从该丢失中恢复，
例如通过重新传输数据、
发送更新的帧或丢弃该帧。
有关更多信息，
请参见{{QUIC-TRANSPORT}}的
第13.2节。


## Acknowledgement-based Detection {#ack-loss-detection}

Acknowledgement-based loss detection implements the spirit of TCP's Fast
Retransmit {{?RFC5681}}, Early Retransmit {{?RFC5827}}, FACK {{FACK}}, SACK loss
recovery {{?RFC6675}}, and RACK {{?RACK=I-D.ietf-tcpm-rack}}. This section
provides an overview of how these algorithms are implemented in QUIC.

A packet is declared lost if it meets all the following conditions:

* The packet is unacknowledged, in-flight, and was sent prior to an
  acknowledged packet.

* Either its packet number is kPacketThreshold smaller than an acknowledged
  packet ({{packet-threshold}}), or it was sent long enough in the past
  ({{time-threshold}}).

The acknowledgement indicates that a packet sent later was delivered, while the
packet and time thresholds provide some tolerance for packet reordering.

Spuriously declaring packets as lost leads to unnecessary retransmissions and
may result in degraded performance due to the actions of the congestion
controller upon detecting loss.  Implementations that detect spurious
retransmissions and increase the reordering threshold in packets or time MAY
choose to start with smaller initial reordering thresholds to minimize recovery
latency.

### 数据包阈值(Packet Threshold)

根据TCP丢失检测的最佳实践，数据包重新排序阈值（kPacketThreshold）的**建议**初始值为3{{?RFC5681}} {{?RFC6675}}.

某些网络可能表现出较高程度的重新排序，导致发送方检测到可疑丢包。
实施者**可以**使用为TCP开发的算法，例如TCP-NCR {{?RFC4653}}，以提高QUIC的重新排序弹性。

### 时间门槛(Time Threshold) {#time-threshold}

一旦确认了以后的数据包，终端**应该**声明如果在过去发送了一个阈值时间量的早期数据包丢失了。
时间阈值计算方法为kTimeThreshold * max（SRTT，latest_RTT）。
如果在最大确认数据包之前发送的数据包尚未被声明丢失，那么**应该**为剩余时间设置一个定时器。

表达为往返时间乘数的**建议**时间阈值（kTimeThreshold）是9/8。

使用max（SRTT，latest_RTT）可以防止以下两种情况：

* 最新的RTT样本低于SRTT，可能是由于重新排序确认遇到了较短的路径;
* 最新的RTT样本高于SRTT，可能是由于实际RTT持续增加，但平滑后的SRTT还没有赶上。

实现**可以**尝试绝对阈值，阈值前连接，自适应阈值或包含RTT方差。
阈值阈值降低会使得重新排序的弹性范围减小并增加伪重传几率，并且较大的阈值增加了丢失检测延迟。


## 加密重传超时(Crypto Retransmission Timeout)

CRYPTO帧中的数据对于QUIC传输和加密协商至关重要，因此要使用较大的激活超时来重新传输它。

初始加密重传超时应该设置为初始RTT的两倍。

开始时，连接中没有先前的RTT样本。
通过同一网络恢复的连接**应该**使用先前连接的最终平滑后RTT值作为恢复连接的初始RTT。
如果没有先前的RTT可用，或者网络发生变化，则初始RTT**应该**设置为100ms。
当接收到确认时，计算新的RTT并且应该将定时器设置为新计算的平滑RTT的两倍。

当发送加密数据包时，发送方必须为加密超时时段设置一个定时器。
必须在发送新的加密数据包时更新此计时器。
超时后，如果可能，发送方必须重新发送所有未确认的CRYPTO数据。

在服务器验证路径上的客户端地址之前，它可以发送的数据量是有限的，如{{QUIC-TRANSPORT}}中所述。
如果不能发送所有未确认的CRYPTO数据，则应重新发送在初始数据包中发送的所有未确认的CRYPTO数据。
如果无法发送数据，则在从客户端收到数据之前不应设置警报。

因为服务器可能被阻塞直到收到更多的数据包，所以即使没有未确认的CRYPTO数据，客户端也**必须**启动加密重传定时器。
如果计时器到期并且客户端没有要重新传输的CRYPTO数据并且没有握手密钥，它应该在至少1200字节的UDP数据报中发送初始数据包。
如果客户端有握手密钥，它**应该**发送握手数据包。

在没有接收到对新数据包的确认的加密定时器的每个连续到期时，发送方**应该**加倍加密重传超时并为该时段设置定时器。

当加密数据包在传输中时，探测计时器（{{pto}}）不活动。


### 重试和版本协商(Retry and Version Negotiation)

重试或版本协商数据包会导致客户端发送另一个初始数据包Initial，有效地重新启动连接过程并重置拥塞控制和丢失恢复状态，包括重置任何挂起的定时器。
两个数据包都表示已收到初始化Initial但未处理。
这两个数据包都不能被视为对初始化Initial的确认。

然而，客户端**可以**计算服务器的RTT估计值，作为从发送第一个Initial时到收到Retry或Version Negotiation数据包的时间段。
客户端**可以**使用此值为RTT估计器播种，以便后续连接到服务器。

### 丢弃密钥和数据包状态(Discarding Keys and Packet State) {#discarding-packets}

丢弃数据包保护密钥时（参见{{QUIC-TLS}}的第4.9节），无法在确认使用这些密钥发送的所有数据包，因为已经无法再处理它们的确认。
发送方**必须**丢弃与这些数据包关联的所有恢复状态，并务必将它们从传输中的字节数中删除。

端点在开始交换握手数据包后停止发送和接收初始数据包（参见{{QUIC-TRANSPORT}}的第17.2.2.1节）。
此时，丢弃所有正在进行的初始数据包的恢复状态。

当0-RTT被拒绝时，丢弃所有正在进行的0-RTT分组的恢复状态。

如果服务器接受0-RTT，但不缓冲在Initial数据包之前到达的0-RTT数据包，则早期的0-RTT数据包将被声明丢失，但预计这种情况很少发生。

期望是在用它们加密的分组被确认或声明丢失之后丢弃密钥。
但是，只要握手密钥可用，就可以尽快销毁初始机密（参见{{QUIC-TLS}}的第4.10节）。

## 探测超时(Probe Timeout) {#pto}

探测超时（PTO）在ack引出数据处于传输状态但在预期的时间段内未收到确认时触发探测数据包。
PTO使连接能够从丢失尾包或确认中恢复。
QUIC中使用的PTO算法实现了尾部丢失探测{{?TLP=I-D.dukkipati-tcpm-tcp-loss-probe}} {{?RACK}}，
RTO {{?RFC5681}}和F-RTO的可靠性功能TCP {{?RFC5682}}的算法，超时计算基于TCP的重传超时时间{{?RFC6298}}。

### 计算PTO{#Computing PTO}

当发送ack-eiting数据包时，发送方为PTO周期安排计时器，如下所示:

~~~
PTO = smoothed_rtt + max(4*rttvar, kGranularity) + max_ack_delay
~~~

kGranularity, smoothed_rtt, rttvar, and max_ack_delay
在附录{{ld-consts-of-interest}} 和附录 {{ld-vars-of-interest}}
中定义.

PTO周期是发送方应该等待发送
数据包的确认的时长。该时长包括估计的
网络往返时间（smoothed_rtt），估计
的方差（4 * rttvar）和max_ack_delay，
以考虑接收方可能延迟发送确认的最大时间。

PTO值**必须**至少设置为kGranularity，
以避免计时器立即到期。

当PTO计时器到期时，发送方将按照下一节
中的说明探测网络。 PTO周期**必须**设置
为其当前值的两倍。发送方速率的这种指数
降低非常重要，因为PTO可能是由于严重拥塞
导致的数据包丢失或确认造成的。

每次发送ack-eliciting包时，发送方计算
其PTO定时器。如果发送方知道在短时间内
将发送更多的ack-eliciting数据包，则发
送方可以选择通过将定时器设置为更少次来进行优化

### 发送探测包

当PTO计时器到期时，发送方**必须**发送一个
ack-eliciting包作为探测。发送方可以发
送最多两个ack-eliciting数据包，以避免
由于单个数据包丢失而导致昂贵的连续PTO到期。

连续的PTO周期呈指数级增长，因此，随着数据
包继续在网络中丢弃，连接恢复延迟呈指数级增
长。在PTO到期时发送两个包增加了对包丢弃
的弹性，从而降低了连续PTO事件的概率。

在PTO上发送的探测包**必须**是ack-eliciting。
探测包**应该**尽可能携带新数据。当新数据
不可用时，当流控制不允许发送新数据时，探测
包**可以**携带重传的未确认数据，或者机会
性地减少丢失恢复延迟。实现**可以**使用
备用策略来确定探测数据包的内容，包括根据应用程
序的优先级发送新数据或重新传输数据。

当PTO计时器多次到期并且无法发送新数据时，
实现必须在每次发送相同的有效载荷或发送
不同的有效载荷之间进行选择。发送相同的
有效载荷可能更简单，并确保优先级最高的帧
首先到达。每次发送不同的有效载荷减少了虚
假重传的可能性。

当PTO计时器到期时，新的或先前发送的数据
可能无法发送，并且数据包可能仍在发送中。
如果数据包在发送中，可以阻止发送方未来发
送新数据。在这些条件下，发件方**应该**
将仍在发送中的任何数据包标记为丢失。
如果发送方希望保证仍在运行中的数据包送达，
它可以发送一个ack-eliciting数据包并
重新设置PTO定时器。

### 丢失检测Detection {#pto-loss}

当接收到新确认一个或多个分组的ACK帧时，
就可以确认传输中的分组的已经送达或丢失。

PTO计时器到期事件不表示数据包丢失，
并且**禁止**将先前未确认的数据包标
记为丢失。当收到新确认数据包的确认时，
丢包检测按数据包和时间阈值机制的规定
进行，请参阅 {{ack-loss-detection}}。

## 讨论{#Discussion}
大多数常量源自互联网上广泛部署
的TCP实现中的最佳常见实践。例外
情况如下。

选择25ms的较短延迟ack时间是因为
较长的延迟ack可以延迟丢失恢复，
并且对于发包频率低于每25ms一个包
的少量连接，对每个包进行ack有利
于拥塞控制和丢失恢复。

选择默认的初始RTT为100ms，因为
它略高于通常在公网上观察
到的中位数和平均min_rtt。

# 拥塞控制 {#congestion-control}

QUIC的拥塞控制基于TCP NewReno {{?RFC6582}}。
 NewReno是基于拥塞窗口的拥塞控制。由于
更精细的控制和适当的字节计数的简易性，QUIC
以字节而不是数据包指定拥塞窗口
{{?RFC3465}}。

QUIC主机**禁止**发送数据包，如果它们会增加
可用拥塞窗口之外的bytes_in_flight（在
附录B.2中定义），除非该数据包是在PTO定
时器到期后发送的探测数据包，如
{{pto}}所述。

实现可以使用其他拥塞控制算法，例如Cubic
 {{?RFC8312}}，终端**可以**使用彼此不
同的算法。 QUIC提供的用于拥塞控制的指标
是通用的，并且被设计为支持不同的算法。

## 显式拥塞通知{#congestion-ecn}

如果已验证路径支持ECN，则QUIC会把
IP报头中的Congestion Experienced
码点作为拥塞信号。本文规定了一个
当终端收到带有Congestion
 Experienced码点的数据包时，终端
的响应，正如[RFC8311]中所讨论的那样，
允许终端尝试其他响应函数。

## 慢启动 {#Slow Start}

QUIC在开始每个连接时慢启动,在丢失
或增加ECN-CE计数器时退出慢启动。
当拥塞窗口小于ssthresh时
QUIC都会重新进入慢启动，通常只
发生在ssthresh之后PTO。在慢启动
时，QUIC会将拥塞窗口的大小增加
处理每个确认时确认的字节数。

## 拥塞避免{#Congestion Avoidance}
慢启动结束为拥塞避免。 NewReno中的
拥塞避免使用加法增加乘法减少（AIMD）
的方法将每个确认的拥塞窗口增加一个
最大数据包大小.当检测到丢失时，
NewReno减半拥塞窗口并将慢启动阈值
设置为新的拥堵窗口。

## 恢复期(Recovery Period) {#recovery period}

恢复是从检测到丢失数据包或增加ECN-CE计数器开始的一段时间。
由于QUIC不重新传输数据包，因此在恢复期发送的第一个数据包意
味着恢复期结束。这与TCP对恢复的定义略有不同，TCP对恢复
的定义当丢失的数据开始重传的时候结束恢复过程。

恢复期将拥塞窗口减少限制为每次往返一次。在恢复期间，无论
ECN-CE计数器中的新损失或增加，拥塞窗口保持不变。

## 忽略不可加密数据包的丢失(Ignoring Loss of Undecryptable Packets)

在握手期间，当数据包到达时，某些数据包保护密钥可能不可用。 特别是，在初始数据包到达之前，不能处理握手和0-RTT数据包，
并且在握手完成之前无法处理1-RTT数据包。端点**可以**忽略在对端
具有用于处理这些分组的分组保护密钥之前可能到达的握手，
0-RTT和1-RTT分组的丢失。

## 探测超时(Probe Timeout)

拥塞控制器**禁止**阻止探测包。但是，发送方**必须**将这些数据包
当作额外的在发送中的包，因为这些数据包会增加网络负载而不会造
成数据包丢失。 请注意，发送探测包可能会导致发送方的传输字节超
过拥塞窗口，直到收到确认数据包丢失或传送的确认为止。

当接收到ACK帧以确定在阈值数量的连续PTO之前发送的所有正在
进行的分组丢失（pto_count大于kPersistentCongestionThreshold，参见
{{cc-consts-of-interest}}），则认为网络正在经历持续拥塞，并且发送者的拥塞
窗口**必须**减少到最小拥塞窗口（kMinimumWindow）。 将拥塞窗口折叠为持久
拥塞的这种响应在功能上类似于发送者对TCP{{RFC5681}}中的重传超时（RTO）的响应。

## 定步过程(Pacing) {#pacing}

本文档未指定起搏器，但**建议**发送方根据来自拥塞控制器的输入
加快所有传输中数据包的发送速度。例如，当与基于窗口的控制器
一起使用时，起搏器可能会在SRTT上分布拥塞窗口，并且起搏器
可能使用基于速率的控制器的速率估计。

实现应该注意构建其拥塞控制器，以便与起搏器很好地配合使用。
例如，起搏器可以包装拥塞控制器并控制拥塞窗口的可用性，
或者起搏器可以调整由拥塞控制器递送给它的分组的速度。
及时交付ACK帧对于高效的丢失恢复非常重要。因此，不应
对仅包含ACK帧的数据包进行定步，以避免延迟其向对等体的传送。

作为流定步器的公知和公开可用实现的示例，实现者被称为Linux
中的公平队列分组调度器(Fq Qdisk)(3.11及更高版本)。

## 在空闲期后发送数据(Sending data after an idle period)

如果发送方停止发送数据并且没有发送中的字节，则它将变为空闲。
发送方的拥塞窗口在空闲时**禁止**增加。

在空闲后发送数据时，发送方必须将其拥塞窗口重置为初始拥塞窗口（参见
{{?RFC5681}}），除非它按比例发送数据包。如果发送方超过初始拥塞窗口
发送任何数据包，则发送方**可以**保留其拥塞窗口。

发送方**可以**实现备用机制，以在空闲时段之后更新其拥塞窗口，例如{{?RFC7661}}
中针对TCP提出的那些。

## 应用限制发送(Application Limited Sending)

当没有充分利用时，不应该在慢启动或拥塞避免中增加拥塞窗口。 由于应用程序数据或流量控制信用不足，拥塞窗口可能未得到充分利用。

调度数据包的发送方（参见{{pacing}}）可能会延迟发送数据包，并且由于此延迟
而无法充分利用拥塞窗口。 如果发送者在没有起搏延迟的情况下完全利用拥塞窗
口，则不考虑应用限制。


# 安全考虑(Security Considerations)

## 拥塞信号(Congestion Signals)

拥塞控制从根本上涉及来自未经认证的实体的信号（丢失和ECN代码点）的消耗。 路径上的攻击者可以伪造或改变这些信号。攻击者可以通过丢弃数据包或通过
更改ECN代码点来更改发送速率来降低发送速率。

## 流量分析(Traffic Analysis)

可以通过观察分组大小来启发式地识别仅携带ACK帧的分组。
确认模式可能会暴露有关链接特征或应用程序行为的信息。
端点可以使用PADDING帧或将确认与其他帧捆绑在一起以减少泄露的信息。

## ECN标记误报(Misreporting ECN Markings)

接收方可能误报ECN标记以改变发送方的拥塞响应。抑制ECN-CE标记的报告
可能导致发送者增加其发送速率。这种增加可能导致拥堵和损失。

发送方**可以**通过标记它们与ECN-CE一起发送的临时数据包来尝试检测报告
的抑制。如果在确认数据包时没有报告标记有ECN-CE的数据包已被标记，
则发送方**应该**为该路径禁用ECN。

报告额外的ECN-CE标记将导致发送方降低其发送速率，这与广告减少的连接
流控制限制类似，因此这样做没有获得优势。

端点选择他们使用的拥塞控制器。虽然拥塞控制器通常将ECN-CE标记的报告
视为等同于丢[RFC8311]，但每个控制器的确切响应可能不同。因此，很难
检测到无法正确回应有关ECN标记的信息。


# IANA注意事项(IANA Considerations)

然而，本文档没有IANA相关使用。

--- back

# Loss Recovery Pseudocode

We now describe an example implementation of the loss detection mechanisms
described in {{loss-detection}}.

## Tracking Sent Packets {#tracking-sent-packets}

To correctly implement congestion control, a QUIC sender tracks every
ack-eliciting packet until the packet is acknowledged or lost.
It is expected that implementations will be able to access this information by
packet number and crypto context and store the per-packet fields
({{sent-packets-fields}}) for loss recovery and congestion control.

After a packet is declared lost, it SHOULD be tracked for an amount of time
comparable to the maximum expected packet reordering, such as 1 RTT.  This
allows for detection of spurious retransmissions.

Sent packets are tracked for each packet number space, and ACK
processing only applies to a single space.

### Sent Packet Fields {#sent-packets-fields}

packet_number:
: The packet number of the sent packet.

ack_eliciting:
: A boolean that indicates whether a packet is ack-eliciting.
  If true, it is expected that an acknowledgement will be received,
  though the peer could delay sending the ACK frame containing it
  by up to the MaxAckDelay.

in_flight:
: A boolean that indicates whether the packet counts towards bytes in
  flight.

is_crypto_packet:
: A boolean that indicates whether the packet contains
  cryptographic handshake messages critical to the completion of the QUIC
  handshake. In this version of QUIC, this includes any packet with the long
  header that includes a CRYPTO frame.

sent_bytes:
: The number of bytes sent in the packet, not including UDP or IP
  overhead, but including QUIC framing overhead.

time_sent:
: The time the packet was sent.


## Constants of interest {#ld-consts-of-interest}

Constants used in loss recovery are based on a combination of RFCs, papers, and
common practice.  Some may need to be changed or negotiated in order to better
suit a variety of environments.

kPacketThreshold:
: Maximum reordering in packets before packet threshold loss detection
  considers a packet lost. The RECOMMENDED value is 3.

kTimeThreshold:

: Maximum reordering in time before time threshold loss detection
  considers a packet lost. Specified as an RTT multiplier. The RECOMMENDED
  value is 9/8.

kGranularity:

: Timer granularity. This is a system-dependent value.  However, implementations
  SHOULD use a value no smaller than 1ms.

kInitialRtt:
: The RTT used before an RTT sample is taken. The RECOMMENDED value is 100ms.

kPacketNumberSpace:
: An enum to enumerate the three packet number spaces.
~~~
  enum kPacketNumberSpace {
    Initial,
    Handshake,
    ApplicationData,
  }
~~~

## Variables of interest {#ld-vars-of-interest}

Variables required to implement the congestion control mechanisms
are described in this section.

loss_detection_timer:
: Multi-modal timer used for loss detection.

crypto_count:
: The number of times all unacknowledged CRYPTO data has been
  retransmitted without receiving an ack.

pto_count:
: The number of times a PTO has been sent without receiving an ack.

time_of_last_sent_ack_eliciting_packet:
: The time the most recent ack-eliciting packet was sent.

time_of_last_sent_crypto_packet:
: The time the most recent crypto packet was sent.

largest_acked_packet[`kPacketNumberSpace`]:
: The largest packet number acknowledged in the packet number space so far.

latest_rtt:
: The most recent RTT measurement made when receiving an ack for
  a previously unacked packet.

smoothed_rtt:
: The smoothed RTT of the connection, computed as described in
  {{?RFC6298}}

rttvar:
: The RTT variance, computed as described in {{?RFC6298}}

min_rtt:
: The minimum RTT seen in the connection, ignoring ack delay.

max_ack_delay:
: The maximum amount of time by which the receiver intends to delay
  acknowledgments, in milliseconds.  The actual ack_delay in a
  received ACK frame may be larger due to late timers, reordering,
  or lost ACKs.

loss_time[`kPacketNumberSpace`]:
: The time at which the next packet in that packet number space will be
  considered lost based on exceeding the reordering window in time.

sent_packets[`kPacketNumberSpace`]:
: An association of packet numbers in a packet number space to information
  about them.  Described in detail above in {{tracking-sent-packets}}.


## Initialization

At the beginning of the connection, initialize the loss detection variables as
follows:

~~~
   loss_detection_timer.reset()
   crypto_count = 0
   pto_count = 0
   smoothed_rtt = 0
   rttvar = 0
   min_rtt = infinite
   time_of_last_sent_ack_eliciting_packet = 0
   time_of_last_sent_crypto_packet = 0
   for pn_space in [ Initial, Handshake, ApplicatonData ]:
     largest_acked_packet[pn_space] = 0
     loss_time[pn_space] = 0
~~~


## On Sending a Packet

After a packet is sent, information about the packet is stored.  The parameters
to OnPacketSent are described in detail above in {{sent-packets-fields}}.

Pseudocode for OnPacketSent follows:

~~~
 OnPacketSent(packet_number, pn_space, ack_eliciting,
              in_flight, is_crypto_packet, sent_bytes):
   sent_packets[pn_space][packet_number].packet_number =
                                            packet_number
   sent_packets[pn_space][packet_number].time_sent = now
   sent_packets[pn_space][packet_number].ack_eliciting =
                                            ack_eliciting
   sent_packets[pn_space][packet_number].in_flight = in_flight
   if (in_flight):
     if (is_crypto_packet):
       time_of_last_sent_crypto_packet = now
     if (ack_eliciting):
       time_of_last_sent_ack_eliciting_packet = now
     OnPacketSentCC(sent_bytes)
     sent_packets[pn_space][packet_number].size = sent_bytes
     SetLossDetectionTimer()
~~~


## On Receiving an Acknowledgment {#on-ack-received}

When an ACK frame is received, it may newly acknowledge any number of packets.

Pseudocode for OnAckReceived and UpdateRtt follow:

~~~
OnAckReceived(ack, pn_space):
  largest_acked_packet[pn_space] = max(largest_acked_packet,
                              ack.largest_acked)

  // If the largest acknowledged is newly acked and
  // ack-eliciting, update the RTT.
  if (sent_packets[pn_space][ack.largest_acked] &&
      sent_packets[pn_space][ack.largest_acked].ack_eliciting):
    latest_rtt =
      now - sent_packets[pn_space][ack.largest_acked].time_sent
    UpdateRtt(latest_rtt, ack.ack_delay)

  // Process ECN information if present.
  if (ACK frame contains ECN information):
      ProcessECN(ack)

  // Find all newly acked packets in this ACK frame
  newly_acked_packets = DetermineNewlyAckedPackets(ack, pn_space)
  if (newly_acked_packets.empty()):
    return

  for acked_packet in newly_acked_packets:
    OnPacketAcked(acked_packet.packet_number, pn_space)

  DetectLostPackets(pn_space)

  crypto_count = 0
  pto_count = 0

  SetLossDetectionTimer()


UpdateRtt(latest_rtt, ack_delay):
  // min_rtt ignores ack delay.
  min_rtt = min(min_rtt, latest_rtt)
  // Limit ack_delay by max_ack_delay
  ack_delay = min(ack_delay, max_ack_delay)
  // Adjust for ack delay if it's plausible.
  if (latest_rtt - min_rtt > ack_delay):
    latest_rtt -= ack_delay
  // Based on {{?RFC6298}}.
  if (smoothed_rtt == 0):
    smoothed_rtt = latest_rtt
    rttvar = latest_rtt / 2
  else:
    rttvar_sample = abs(smoothed_rtt - latest_rtt)
    rttvar = 3/4 * rttvar + 1/4 * rttvar_sample
    smoothed_rtt = 7/8 * smoothed_rtt + 1/8 * latest_rtt
~~~


## On Packet Acknowledgment

When a packet is acknowledged for the first time, the following OnPacketAcked
function is called.  Note that a single ACK frame may newly acknowledge several
packets. OnPacketAcked must be called once for each of these newly acknowledged
packets.

OnPacketAcked takes two parameters: acked_packet, which is the struct detailed
in {{sent-packets-fields}}, and the packet number space that this ACK frame was
sent for.

Pseudocode for OnPacketAcked follows:

~~~
   OnPacketAcked(acked_packet, pn_space):
     if (acked_packet.ack_eliciting):
       OnPacketAckedCC(acked_packet)
     sent_packets[pn_space].remove(acked_packet.packet_number)
~~~


## Setting the Loss Detection Timer

QUIC loss detection uses a single timer for all timeout loss detection.  The
duration of the timer is based on the timer's mode, which is set in the packet
and timer events further below.  The function SetLossDetectionTimer defined
below shows how the single timer is set.

This algorithm may result in the timer being set in the past, particularly if
timers wake up late. Timers set in the past SHOULD fire immediately.

Pseudocode for SetLossDetectionTimer follows:

~~~
// Returns the earliest loss_time and the packet number
// space it's from.  Returns 0 if all times are 0.
GetEarliestLossTime():
  time = loss_time[Initial]
  space = Initial
  for pn_space in [ Handshake, ApplicatonData ]:
    if loss_time[pn_space] != 0 &&
       (time == 0 || loss_time[pn_space] < time):
      time = loss_time[pn_space];
      space = pn_space
  return time, space

SetLossDetectionTimer():
  // Don't arm timer if there are no ack-eliciting packets
  // in flight.
  if (no ack-eliciting packets in flight):
    loss_detection_timer.cancel()
    return

  loss_time, _ = GetEarliestLossTime()
  if (loss_time != 0):
    // Time threshold loss detection.
    loss_detection_timer.update(loss_time)
    return

  if (crypto packets are in flight):
    // Crypto retransmission timer.
    if (smoothed_rtt == 0):
      timeout = 2 * kInitialRtt
    else:
      timeout = 2 * smoothed_rtt
    timeout = max(timeout, kGranularity)
    timeout = timeout * (2 ^ crypto_count)
    loss_detection_timer.update(
      time_of_last_sent_crypto_packet + timeout)
    return

  // Calculate PTO duration
  timeout =
    smoothed_rtt + 4 * rttvar + max_ack_delay
  timeout = max(timeout, kGranularity)
  timeout = timeout * (2 ^ pto_count)

  loss_detection_timer.update(
    time_of_last_sent_ack_eliciting_packet + timeout)
~~~


## On Timeout

When the loss detection timer expires, the timer's mode determines the action
to be performed.

Pseudocode for OnLossDetectionTimeout follows:

~~~
OnLossDetectionTimeout():
  loss_time, pn_space = GetEarliestLossTime()
  if (loss_time != 0):
    // Time threshold loss Detection
    DetectLostPackets(pn_space)
  // Retransmit crypto data if no packets were lost
  // and there are still crypto packets in flight.
  else if (crypto packets are in flight):
    // Crypto retransmission timeout.
    RetransmitUnackedCryptoData()
    crypto_count++
  else:
    // PTO
    SendOneOrTwoPackets()
    pto_count++

  SetLossDetectionTimer()
~~~


## Detecting Lost Packets

DetectLostPackets is called every time an ACK is received and operates on
the sent_packets for that packet number space. If the loss detection timer
expires and the loss_time is set, the previous largest acknowledged packet
is supplied.

Pseudocode for DetectLostPackets follows:

~~~
DetectLostPackets(pn_space):
  loss_time[pn_space] = 0
  lost_packets = {}
  loss_delay = kTimeThreshold * max(latest_rtt, smoothed_rtt)

  // Packets sent before this time are deemed lost.
  lost_send_time = now() - loss_delay

  // Packets with packet numbers before this are deemed lost.
  lost_pn = largest_acked_packet - kPacketThreshold

  foreach unacked in sent_packets:
    if (unacked.packet_number > largest_acked_packet):
      continue

    // Mark packet as lost, or set time when it should be marked.
    if (unacked.time_sent <= lost_send_time ||
        unacked.packet_number <= lost_pn):
      sent_packets.remove(unacked.packet_number)
      if (unacked.in_flight):
        lost_packets.insert(unacked)
    else:
      if (loss_time[pn_space] == 0):
        loss_time[pn_space] = unacked.time_sent + loss_delay
      else:
        loss_time[pn_space] = min(loss_time[pn_space],
                                  unacked.time_sent + loss_delay)

  // Inform the congestion controller of lost packets and
  // let it decide whether to retransmit immediately.
  if (!lost_packets.empty()):
    OnPacketsLost(lost_packets)
~~~


# Congestion Control Pseudocode

We now describe an example implementation of the congestion controller described
in {{congestion-control}}.

## Constants of interest {#cc-consts-of-interest}

Constants used in congestion control are based on a combination of RFCs,
papers, and common practice.  Some may need to be changed or negotiated
in order to better suit a variety of environments.

kMaxDatagramSize:
: The sender's maximum payload size. Does not include UDP or IP overhead.  The
  max packet size is used for calculating initial and minimum congestion
  windows. The RECOMMENDED value is 1200 bytes.

kInitialWindow:
: Default limit on the initial amount of data in flight, in bytes.  Taken from
  {{?RFC6928}}.  The RECOMMENDED value is the minimum of 10 * kMaxDatagramSize
  and max(2* kMaxDatagramSize, 14600)).

kMinimumWindow:
: Minimum congestion window in bytes. The RECOMMENDED value is
  2 * kMaxDatagramSize.

kLossReductionFactor:
: Reduction in congestion window when a new loss event is detected.
  The RECOMMENDED value is 0.5.

kPersistentCongestionThreshold:
: Number of consecutive PTOs required for persistent congestion to be
  established.  The rationale for this threshold is to enable a sender to use
  initial PTOs for aggressive probing, as TCP does with Tail Loss Probe (TLP)
  {{TLP}} {{RACK}}, before establishing persistent congestion, as TCP does with
  a Retransmission Timeout (RTO) {{?RFC5681}}.  The RECOMMENDED value for
  kPersistentCongestionThreshold is 2, which is equivalent to having two TLPs
  before an RTO in TCP.


## Variables of interest {#vars-of-interest}

Variables required to implement the congestion control mechanisms
are described in this section.

ecn_ce_counter:
: The highest value reported for the ECN-CE counter by the peer in an ACK
  frame. This variable is used to detect increases in the reported ECN-CE
  counter.

bytes_in_flight:
: The sum of the size in bytes of all sent packets that contain at least one
  ack-eliciting or PADDING frame, and have not been acked or declared
  lost. The size does not include IP or UDP overhead, but does include the QUIC
  header and AEAD overhead.  Packets only containing ACK frames do not count
  towards bytes_in_flight to ensure congestion control does not impede
  congestion feedback.

congestion_window:
: Maximum number of bytes-in-flight that may be sent.

recovery_start_time:
: The time when QUIC first detects a loss, causing it to enter recovery.
  When a packet sent after this time is acknowledged, QUIC exits recovery.

ssthresh:
: Slow start threshold in bytes.  When the congestion window is below ssthresh,
  the mode is slow start and the window grows by the number of bytes
  acknowledged.


## Initialization

At the beginning of the connection, initialize the congestion control
variables as follows:

~~~
   congestion_window = kInitialWindow
   bytes_in_flight = 0
   recovery_start_time = 0
   ssthresh = infinite
   ecn_ce_counter = 0
~~~


## On Packet Sent

Whenever a packet is sent, and it contains non-ACK frames, the packet
increases bytes_in_flight.

~~~
   OnPacketSentCC(bytes_sent):
     bytes_in_flight += bytes_sent
~~~


## On Packet Acknowledgement

Invoked from loss detection's OnPacketAcked and is supplied with the
acked_packet from sent_packets.

~~~
   InRecovery(sent_time):
     return sent_time <= recovery_start_time

   OnPacketAckedCC(acked_packet):
     // Remove from bytes_in_flight.
     bytes_in_flight -= acked_packet.size
     if (InRecovery(acked_packet.time_sent)):
       // Do not increase congestion window in recovery period.
       return
     if (IsAppLimited())
       // Do not increase congestion_window if application
       // limited.
       return
     if (congestion_window < ssthresh):
       // Slow start.
       congestion_window += acked_packet.size
     else:
       // Congestion avoidance.
       congestion_window += kMaxDatagramSize * acked_packet.size
           / congestion_window
~~~


## On New Congestion Event

Invoked from ProcessECN and OnPacketsLost when a new congestion event is
detected. May start a new recovery period and reduces the congestion
window.

~~~
   CongestionEvent(sent_time):
     // Start a new congestion event if the sent time is larger
     // than the start time of the previous recovery epoch.
     if (!InRecovery(sent_time)):
       recovery_start_time = Now()
       congestion_window *= kLossReductionFactor
       congestion_window = max(congestion_window, kMinimumWindow)
       ssthresh = congestion_window
       // Collapse congestion window if persistent congestion
       if (pto_count > kPersistentCongestionThreshold):
         congestion_window = kMinimumWindow
~~~


## Process ECN Information

Invoked when an ACK frame with an ECN section is received from the peer.

~~~
   ProcessECN(ack):
     // If the ECN-CE counter reported by the peer has increased,
     // this could be a new congestion event.
     if (ack.ce_counter > ecn_ce_counter):
       ecn_ce_counter = ack.ce_counter
       // Start a new congestion event if the last acknowledged
       // packet was sent after the start of the previous
       // recovery epoch.
       CongestionEvent(sent_packets[ack.largest_acked].time_sent)
~~~


## On Packets Lost

Invoked by loss detection from DetectLostPackets when new packets
are detected lost.

~~~
   OnPacketsLost(lost_packets):
     // Remove lost packets from bytes_in_flight.
     for (lost_packet : lost_packets):
       bytes_in_flight -= lost_packet.size
     largest_lost_packet = lost_packets.last()

     // Start a new congestion epoch if the last lost packet
     // is past the end of the previous recovery epoch.
     CongestionEvent(largest_lost_packet.time_sent)
~~~


# Change Log

> **RFC Editor's Note:**  Please remove this section prior to
> publication of a final version of this document.

Issue and pull request numbers are listed with a leading octothorp.

## Since draft-ietf-quic-recovery-17

- After Probe Timeout discard in-flight packets or send another (#2212, #1965)
- Endpoints discard initial keys as soon as handshake keys are available (#1951,
  #2045)
- 0-RTT state is discarded when 0-RTT is rejected (#2300)
- Loss detection timer is cancelled when ack-eliciting frames are in flight
  (#2117, #2093)
- Packets are declared lost if they are in flight (#2104)
- After becoming idle, either pace packets or reset the congestion controller
  (#2138, 2187)
- Process ECN counts before marking packets lost (#2142)
- Mark packets lost before resetting crypto_count and pto_count (#2208, #2209)
- Congestion and loss recovery state are discarded when keys are discarded
  (#2327)


## Since draft-ietf-quic-recovery-16

- Unify TLP and RTO into a single PTO; eliminate min RTO, min TLP and min crypto
  timeouts; eliminate timeout validation (#2114, #2166, #2168, #1017)
- Redefine how congestion avoidance in terms of when the period starts (#1928,
  #1930)
- Document what needs to be tracked for packets that are in flight (#765, #1724,
  #1939)
- Integrate both time and packet thresholds into loss detection (#1969, #1212,
  #934, #1974)
- Reduce congestion window after idle, unless pacing is used (#2007, #2023)
- Disable RTT calculation for packets that don't elicit acknowledgment (#2060,
  #2078)
- Limit ack_delay by max_ack_delay (#2060, #2099)
- Initial keys are discarded once Handshake are avaialble (#1951, #2045)
- Reorder ECN and loss detection in pseudocode (#2142)
- Only cancel loss detection timer if ack-eliciting packets are in flight
  (#2093, #2117)


## Since draft-ietf-quic-recovery-14

- Used max_ack_delay from transport params (#1796, #1782)
- Merge ACK and ACK_ECN (#1783)

## Since draft-ietf-quic-recovery-13

- Corrected the lack of ssthresh reduction in CongestionEvent pseudocode (#1598)
- Considerations for ECN spoofing (#1426, #1626)
- Clarifications for PADDING and congestion control (#837, #838, #1517, #1531,
  #1540)
- Reduce early retransmission timer to RTT/8 (#945, #1581)
- Packets are declared lost after an RTO is verified (#935, #1582)


## Since draft-ietf-quic-recovery-12

- Changes to manage separate packet number spaces and encryption levels (#1190,
  #1242, #1413, #1450)
- Added ECN feedback mechanisms and handling; new ACK_ECN frame (#804, #805,
  #1372)


## Since draft-ietf-quic-recovery-11

No significant changes.

## Since draft-ietf-quic-recovery-10

- Improved text on ack generation (#1139, #1159)
- Make references to TCP recovery mechanisms informational (#1195)
- Define time_of_last_sent_handshake_packet (#1171)
- Added signal from TLS the data it includes needs to be sent in a Retry packet
  (#1061, #1199)
- Minimum RTT (min_rtt) is initialized with an infinite value (#1169)

## Since draft-ietf-quic-recovery-09

No significant changes.

## Since draft-ietf-quic-recovery-08

- Clarified pacing and RTO (#967, #977)

## Since draft-ietf-quic-recovery-07

- Include Ack Delay in RTO(and TLP) computations (#981)
- Ack Delay in SRTT computation (#961)
- Default RTT and Slow Start (#590)
- Many editorial fixes.

## Since draft-ietf-quic-recovery-06

No significant changes.

## Since draft-ietf-quic-recovery-05

- Add more congestion control text (#776)

## Since draft-ietf-quic-recovery-04

No significant changes.

## Since draft-ietf-quic-recovery-03

No significant changes.

## Since draft-ietf-quic-recovery-02

- Integrate F-RTO (#544, #409)
- Add congestion control (#545, #395)
- Require connection abort if a skipped packet was acknowledged (#415)
- Simplify RTO calculations (#142, #417)


## Since draft-ietf-quic-recovery-01

- Overview added to loss detection
- Changes initial default RTT to 100ms
- Added time-based loss detection and fixes early retransmit
- Clarified loss recovery for handshake packets
- Fixed references and made TCP references informative


## Since draft-ietf-quic-recovery-00

- Improved description of constants and ACK behavior


## Since draft-iyengar-quic-loss-recovery-01

- Adopted as base for draft-ietf-quic-recovery
- Updated authors/editors list
- Added table of contents


# Acknowledgments
{:numbered="false"}
