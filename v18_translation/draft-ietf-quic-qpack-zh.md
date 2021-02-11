---
title: "QPACK: Header Compression for HTTP over QUIC"
abbrev: QPACK
docname: draft-ietf-quic-qpack-latest
date: {DATE}
category: std
ipr: trust200902
area: Transport
workgroup: QUIC

stand_alone: yes
pi: [toc, sortrefs, symrefs, docmapping]

author:
 -
    ins: C. Krasic
    name: Charles 'Buck' Krasic
    org: Netflix
    email: ckrasic@netflix.com
 -
    ins: M. Bishop
    name: Mike Bishop
    org: Akamai Technologies
    email: mbishop@evequefou.be
 -
    ins: A. Frindell
    name: Alan Frindell
    org: Facebook
    email: afrind@fb.com
    role: editor


normative:

  HTTP3:
    title: "Hypertext Transfer Protocol Version 3 (HTTP/3)"
    date: {DATE}
    seriesinfo:
      Internet-Draft: draft-ietf-quic-http-latest
    author:
      -
          ins: M. Bishop
          name: Mike Bishop
          org: Akamai Technologies
          role: editor

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


--- abstract

This specification defines QPACK, a compression format for efficiently
representing HTTP header fields, to be used in HTTP/3. This is a variation of
HPACK header compression that seeks to reduce head-of-line blocking.

--- note_Note_to_Readers

Discussion of this draft takes place on the QUIC working group mailing list
(quic@ietf.org), which is archived at
<https://mailarchive.ietf.org/arch/search/?email_list=quic>.

Working Group information can be found at <https://github.com/quicwg>; source
code and issues list for this draft can be found at
<https://github.com/quicwg/base-drafts/labels/-qpack>.

--- middle

# 简介(Introduction)

QUIC 传输协议从一开始就设计为支持 HTTP 语义，其设计包含了 HTTP/2 的许多特性。
HTTP/2使用 HPACK({{!RFC7541}})进行报头压缩，但 QUIC 的流复用与 HPACK 发生了一些冲突。
QUIC设计的一个关键目标是通过减少队头阻塞来改进相对于 HTTP/2 的流的多路复用。
如果 HPACK 用于 HTTP/3，由于它内建的所有流上的帧之间的总排序的假设，会导致队头阻塞。

QUIC 描述在{{QUIC-TRANSPORT}}中。
HTTP/3 映射描述于{{HTTP3}}。
对于 HTTP/2 的详细描述，参见{{?RFC7540}}。
HPACK 的描述详见{{!RFC7541}}。

QPACK 重新使用了 HPACK 的核心概念，但经过重新设计，
在针对队头阻塞的恢复能力和最佳压缩比做平衡，允许在出现无序交付的情况下保持正确性，具有实现的灵活性。
设计目标是在相同的损耗条件下，以实质上较少的队头阻塞达到接近 HPACK 的压缩比。

## 惯例与定义(Conventions and Definitions)

关键词 **"必须(MUST)”， "禁止(MUST NOT)"， "必需(REQUIRED)"，
"应当(SHALL)"， "应当不(SHALL NOT)"， "应该(SHOULD)"，
"不应该(SHOULD NOT)"， "推荐(RECOMMENDED)"，
"不推荐(NOT RECOMMENDED)"， "可以(MAY)"， "可选(OPTIONAL)"**
在这篇文档中将会如 BCP 14 {{!RFC2119}} {{!RFC8174}} 中描述的，
当且仅当他们如此例子显示的以加粗的形式出现时。
文档中使用的术语在下方描述。

头字段(Header field):

: 作为 HTTP 消息的一部分发送的键值对。

头列表(Header list):

: 和一个 HTTP 消息关联的有序的头字段的集合。一个头列表可以包含多个同键名的头字段。也可以包含重复的头字段。

头区块(Header block):

: 头列表的压缩表示。

编码器(Encoder):

: 将头列表转化成头区块的实现。

解码器(Decoder):

: 将头区块转化成头列表的实现。

完全索引(Absolute Index):

: 动态表中每一记录的唯一索引。

基准(Base):

: 指向关联索引的引用。动态引用用于关联到头取款中的某个基准。

插入数(Insert Count):

: 动态表中插入的记录总的数量。

QPACK 是一个名字，不是一个缩写。

## 全局惯例(Notational Conventions)

示意图使用了描述在 {{?RFC2360}}中3.1章的格式，包含以下额外的惯例:

x (A)
: 表示 X 是 A 位长

x (A+)
: 表示 X 使用了定义于[RFC7541]中5.1章的，以A位的前缀开始。

x ...
: 表示 x 是变长的，并延展到区域末端。

# 压缩处理概述 {#Compression Process Overview}

与HPACK一样，QPACK使用两个表来将头字段与索引相关联。该
静态表（请参阅{{table-static}}）是预定义的，包含公共标题
字段（其中一些值为空值）。动态表（见
{{table-dynamic}}）是在连接过程中构建的，可以使用
由编码器索引编码后标题列表中的标题字段。

QPACK指令出现在三种不同类型的流中：

 - 编码器使用单向流来修改动态表的状态，
不会发出与任何特定请求相关联的头字段。

 - 请求和推送流中的HEADERS和PUSH_PROMISE帧在不修改
表状态的情况下引用表．

 - 解码器在单向流上向编码器发送反馈。这个
反馈使编码器能够管理动态表状态。

## 编码器 ｛#Encoder}　

编码器通过为每个列表中的头部字段发出索引
或文字表示的方式来压缩头部列表．
引用静态表和文字表示不需要任何动态状态，也
没有线头阻塞的风险。
如果编码器没有收到某个条目的确认，动态表
的引用就会有线头阻塞的风险，表明该条目可以
从解码处获得．

编码器**可以**在它选择的动态表中插入任何条目;不限
于正在压缩的头部字段．

QPACK保留每个头部列表中头部字段的顺序。一个
编码器**必须**按照它们在头部列表中出现的顺序
发出头部字段标识．

QPACK旨在将更复杂的状态跟踪包含在编码器中，
而解码器相对简单。

### 引用追踪 (Reference Tracking)

编码器**必须**确保引用动态表项的报头块在被引用的条目删除后不会被解码器接收。
因此，编码器需要跟踪关于引用动态表的每个压缩报头块的信息，直到解码器确认该报头块为止。

### 阻塞动态表插入 (Blocked Dynamic Table Insertions) {#blocked-insertion}

如果这样做会删除具有未确认引用的条目，编码器**不得**将条目插入动态表(或复制现有条目)。
对于可能依赖于新添加条目的报头块，编码器可以使用文字表示。

为了确保编码器不被阻止添加新条目，编码器可以避免引用接近于删除的条目。
编码器可以发出一条重复的指令(参见{{duplicate}})，
而不是引用这样的条目，并引用重复的指令。

确定哪些条目太接近于删除而不能引用是编码器的优先项。
一种启发式方法是针对动态表中的固定数量的可用空间:
要么是未使用的空间，要么是可以通过删除未引用的条目来回收的空间。
为了实现这一点，编码器可以维护一个耗尽索引，这是动态表中最小的可以发出一个引用的绝对索引。
当插入新条目时，编码器会增加耗尽索引，以维护表中它不会引用的部分。
如果编码器没有创建对绝对索引低于耗尽索引的条目的新引用，
那么对这些条目的未确认引用的数量最终将变为零，从而允许将它们清除。


~~~~~~~~~~  drawing
   +----------+---------------------------------+--------+
   | 耗尽 |          可引用的          | 未使用的 |
   | 索引 |           条目             | 空间  |
   +----------+---------------------------------+--------+
   ^          ^                                 ^
   |          |                                 |
  插入    耗尽索引               插入点
  节点
~~~~~~~~~~
{:#fig-draining-index title="耗尽动态表项(Draining Dynamic Table Entries)"}

### 避免报头块阻塞 (Avoiding Head-of-Line Blocking) {#overview-hol-avoidance}

由于QUIC不保证不同流上数据之间的顺序，因此报头块可能引用尚未接收到的动态表中的条目。

每个报头块包含一个所需的插入计数，这是可以解码报头块的插入计数的最小可能值。
对于引用动态表的报头块，所需的插入计数比所有引用的动态表条目的最大绝对索引大1。
对于没有引用动态表的报头块，所需的插入计数为零。

如果解码器遇到一个报头块，其所需的插入计数值大于上面定义的值，
它**可以**将其视为HTTP_QPACK_DECOMPRESSION_FAILED类型的流错误。
如果解码器遇到一个报头块，其所需的插入计数值小于上面定义的值，
它**必须**将其视为HTTP_QPACK_DECOMPRESSION_FAILED类型的流错误，
如{{invalid-references}}所述。

当所需的插入计数为零时，帧不包含对动态表的引用，并且总是可以立即处理。

如果所需的插入计数大于接收到的动态表条目的数量，则认为流是“阻塞的”。
在被阻塞时，报头块数据**应**保留在被阻塞流的流控制窗口中。
当插入计数大于或等于解码器已从流中读取的所有报头块所需的插入计数时，流将被解除阻塞。

SETTINGS_QPACK_BLOCKED_STREAMS设置(参见{{configuration})
指定了可以阻塞的流数量的上限。
编码器**必须**始终将可能被阻塞的流的数量限制为SETTINGS_QPACK_BLOCKED_STREAMS的值。
注意，解码器可能不会在每个可能被阻塞的流上都被阻塞。
如果解码器遇到比它承诺支持的更多的阻塞流，
它**必须**将此视为类型为HTTP_QPACK_DECOMPRESSION_FAILED的流错误。

编码器可以决定是否接收一个有被阻塞的风险的流。
如果SETTINGS_QPACK_BLOCKED_STREAMS的值允许，
通常可以通过引用仍然在传输中的动态表条目来提高压缩效率，
但是如果出现丢失或重新排序流，则可以在解码器上阻塞流。
通过只引用已确认的动态表项，编码器可以避免阻塞的风险，但这可能意味着使用文字。
由于字面值使报头块更大，这可能导致编码器在拥塞或流控制限制下被阻塞。

### 已知接收计数器 (Known Received Count)

为了确定哪些动态表条目可以安全地使用而不会阻塞流，编码器跟踪解码器接收到的条目数量。
已知接收计数跟踪已确认插入的总数。

当允许阻塞引用时，编码器使用报头块确认来维护已知的接收计数，
如{{header-acknowledgement}}所述。

为了确认报头块没有引用的动态表条目，例如因为编码器或解码器选择不冒阻塞流的风险，
解码器发送一条Insert Count Increment指令(参见{{insert-count-increment}})。

## 解码器 (Decoder)

与在HPACK中一样，解码器处理报报头块并发出相应的报头列表。
它还处理来自解码器流上接收的编码器指令的动态表修改。

解码器**必须**按照其出现在输入头块中出现的顺序发出报头字段。


### 状态同步 (State Synchronization)

解码器指令({{decoder-instructions}})中解码器上的信号关键事件，
允许编码器跟踪解码器的状态。这些事件包括:

- 完整的报头块处理
- 可能具有剩余报头块的流的丢弃
- 新的动态表条目的接收

了解到已经处理了包含对动态表的引用的报头块，就允许编码器将不存在未确认引用的条目删除，
而不管这些引用是否可能被阻塞(参见{{blocked-insertion}})。
当流被重置或放弃时，表示这些头块将永远不会被处理的指示也有类似的作用;

解码器选择何时发出插入计数增量指令(参见{{insert-count-increment})。
在添加每个新的动态表条目后发出一条指令，这将向编码器提供最及时的反馈，
但与其他解码器的反馈一起可能是冗余的。
通过延迟插入计数增量指令，解码器可能能够合并多个插入计数增量指令，
或者用报头确认完全替换它们(参见{{header-acknowledgement}})。
但是，如果编码器在使用条目之前等待条目被确认，那么延迟太长可能会导致压缩效率低下。


### 阻塞解码(Blocked Decoding)
每个流中要求插入的计数值可以用于跟踪阻塞的流。每当解码器处理表更新时，它就
可以开始解码任何现在满足其相关性的阻塞流。

# Header Tables

# 头部表(Header Tables)

与HPACK不同，QPACK静态表和动态表中的条目分别寻址。以下各节介绍如何对每个表中
的条目进行寻址。

## 静态表（Static Table） {#table-static}

静态表由预定义的报头字段的静态列表组成，每个字段随时间的推移都具有固定的索引。
其条目在{{static-table}}中定义。

注意，QPACK静态表是从0索引的，而HPACK静态表是从1索引的。

当解码器在报头块指令中遇到无效的静态表索引时，它**必须**将其视为类型为
`HTTP_QPACK_DECOMPRESSION_FAILED`的流错误。如果在编码器流上收到此索引，
则必须将其视为`HTTP_QPACK_ENCODER_STREAM_ERROR`类型的连接错误。

## 动态表（Dynamic Table） {#table-dynamic}

动态表由按先进先出顺序维护的标题字段列表组成。每个HTTP/3端点都保存一个最初
为空的动态表。条目是由在编码器流上接收的编码器指令添加的
(请参阅{{encoder-instructions}})。

动态表可以包含重复的条目(即具有相同名称和相同值的条目)。因此，解码器
**禁止**将重复条目视为错误。


### 动态表大小（Dynamic Table Size）

动态表的大小是其条目大小的总和。

条目的大小是其名称的长度(以字节为单位)(在{{string-literals}}中定义)、
其值的长度(以字节为单位)和32的总和。

条目的大小由不经Huffman编码的条目名称和值的长度算出。


### 动态表容量和驱逐（Dynamic Table Capacity and Eviction） {#eviction}

编码器设置动态表的容量，作为其大小的上限。动态表的初始容量为零。

在将新条目添加到动态表之前，将从动态表的末尾逐出条目，直到动态表的大小于
或等于(表容量-新条目的大小)或直到表为空。除非解码器首先确认了动态表条目，
否则编码器**禁止**将其逐出。

如果新条目的大小小于或等于动态表容量，则该条目将添加到表中。如果编码器
试图添加大于动态表容量的条目，则视为错误；解码器必须将此视为
`HTTP_QPACK_ENCODER_STREAM_ERROR`类型的连接错误。

新条目可以引用动态表中的条目，在将此新条目添加到动态表中时，该条目将被逐出。
如果在插入新条目之前将引用的条目从动态表中逐出，则应注意实现以避免删除引用
的名称或值。

每当动态表容量被编码器减小时，条目从动态表的末尾被逐出，直到动态表的大小于
或等于新的表容量。通过将容量设置为0，可以使用此机制完全清除动态表中的条目，
随后可以恢复该容量。

### 最大动态表容量（Maximum Dynamic Table Capacity）

为了限制解码器的内存要求，解码器限制了允许编码器为动态表容量设置的最大值。在
HTTP/3中，此限制由解码器发送的SETTINGS_QPACK_MAX_TABLE_CAPACITY的值确定
(请参阅{{configuration}})。编码器不能设置超过此最大值的动态表容量，但它可以
选择使用较低的动态表容量(请参见{{set-dynamic-capacity}})。

对于使用HTTP/3中的0-RTT数据的客户端，服务器的最大表容量是设置的记忆值，如果该值
以前未发送，则为零。当客户端的设置的0-RTT值为0时，服务器可以在其SETTINGS帧中将
其设置为非零值。如果记住的值为非零，则服务器必须在其SETTINGS帧中发送相同的非零值。
如果它指定了任何其他值，或者在SETTINGS帧中忽略了SETTINGS_QPACK_MAX_TABLE_CAPACITY，
编码器必须将其视为`HTTP_QPACK_DECODER_STREAM_ERROR`类型的连接错误。

当0-RTT未到达或被拒绝时，对于HTTP/3服务器和HTTP/3客户端，最大表容量为0，直到
编码器处理具有非零值SETTINGS_QPACK_MAX_TABLE_CAPACITY的SETTINGS帧。

当最大表容量为0时，编码器不能向动态表中插入条目，也**禁止**在编码器流上发送任何
编码器指令。

### 绝对索引（Absolute Indexing） {#indexing}

每个条目都具有为该条目的生存期固定的绝对索引和根据引用的上下文而改变的相对索引。
插入的第一个条目具有绝对索引“0”；索引随着每次插入而增加1。

### 相对索引（Relative Indexing）

相对索引从零开始，在与绝对索引相反的方向上增加。确定哪个条目具有相对索引“0”取决于
引用的上下文。

在编码器指令中，相对索引“0”总是指动态表中最近插入的值。请注意，这意味着在解释编码
器流上的指令时，给定相对索引引用的条目将发生更改。

~~~~~ drawing
      +-----+---------------+-------+
      | n-1 |      ...      |   d   |  绝对索引
      + - - +---------------+ - - - +
      |  0  |      ...      | n-d-1 |  相对索引
      +-----+---------------+-------+
      ^                             |
      |                             V
    插入点                        丢弃点

n = 插入的条目计数
d = 已删除的条目计数
~~~~~
{: title="动态表索引-控制流示例"}

与编码器指令不同，标头块指令中的相对索引相对于标头块开始处的基准索引
(请参见{{header-prefix}})。这确保了即使在解码报头块时更新了动态表，引用也是
稳定的。

基准被编码为相对于所需插入计数的值。基准标识了可以使用相对索引引用从添加的最后一个条目
的0开始的哪些动态表条目。

后基准引用用于在基准之后插入的条目，从0开始，对于在基准之后添加的第一个条目，
请参见{{post-base}}。

~~~~~ drawing
 规定的
  插入
  计数        基准
    |           |
    V           V
    +-----+-----+-----+-----+-------+
    | n-1 | n-2 | n-3 | ... |   d   |  绝对索引
    +-----+-----+  -  +-----+   -   +
                |  0  | ... | n-d-3 |  相对索引
                +-----+-----+-------+

n = 插入的条目计数
d = 已删除的条目计数
~~~~~
{: title="表头块中的动态表索引-相对索引示例"}


### 后基准索引 {#post-base}

报头块可以引用在基准标识的条目之后添加的条目。
这允许编码器在一次传输中处理报头块，
并包含对在处理此(或其他)报头块时添加的条目的引用。
使用后基准指令引用新添加的条目。
后基准指令的索引与绝对索引的增长方向相同，
零值是在基准之后插入的第一个条目。

~~~~~ drawing
               基准
                |
                V
    +-----+-----+-----+-----+-----+
    | n-1 | n-2 | n-3 | ... |  d  |  绝对索引
    +-----+-----+-----+-----+-----+
    |  1  |  0  |                    后基准索引
    +-----+-----+

n = 插入的条目计数
d = 已删除的条目计数
~~~~~
{: title="Example Dynamic Table Indexing - Post-Base Index in Header Block"}


### 无效引用 {#invalid-references}

如果解码器在报头块指令中遇到对
已被驱逐的动态表条目的引用，
或者其绝对索引大于或等于声明
所需的插入数(请参见{{header-prefix}})，
则**必须**将其视为`HTTP_QPACK_DURSPAMPAGE_FAILED‘类型的
流错误。

如果解码器在编码器指令中遇到
对已删除的动态表条目的引用，
则**必须**将其视为`HTTP_QPACK_CONTORDER_STREAM_ERROR`类型的
连接错误。

# 线路格式 {#wire-format}

## 原语 {#primitives}

### 前缀整数 {#string-literals}

本文档中大量使用了在[RFC7541]5.1节中提到的前缀整数。
前缀整数的格式和[RFC7541]中的一致。
QPACK实现**必须**能够解码长达62位的整数。

### 字符常量

在[RFC7541]第5.2节定义的字符常量
也在本文档中大量使用，该字符串格式包括
可选的Huffman编码。

HPACK定义了从字节边界开始的字符常量。
它们以单个标志开头(指示字符串是否由Huffman编码)，
然后是编码为7位长度的前缀整数，
最后是数据的长度，字节为单位。
启用Huffman编码后，
无需修改即可使用[RFC7541]附录B中的Huffman表。

本文档扩展了字符常量的定义，
并允许它们从字节边界以外的地方开始。
“N位的前缀字符常量”以相同的
Huffman标志开头，后跟编码为(N-1)位长度的
前缀整数。字符常量的其余部分没有修改。

不带前缀长度的字符常量是一个8位的
前缀字符常量，遵循[RFC7541]中的
定义未作修改。

## 指令

有三个独立的QPACK指令空间。
编码器指令({{encoder-instructions}})携带表更新，
解码器指令({{decoder-instructions}})携带对表修改和
报头处理的确认，而报头块指令({{header-block-instructions}})
通过引用QPACK表状态来传送报头列表的编码表示。

编码器和解码器指令用于
在本节所述的单向流类型上。
报头块指令包含在HEADERS和PUSH_PROMISE帧中，
如{{HTTP3}}所述，这些帧是根据请求或
推送流传送的。

### 编码和解码流

QPACK定义了两种单向流类型:

 - 编码流是类型为“0x02”的单向流。
   它携带了来自编码器的未成帧的编码器指令序列给
   解码器。

 - 解码器流是类型为“0x03`”的单向流。
   它将解码器指令的未成帧序列从解码器传送到编码器。

<!-- s/exactly/no more than/  ? -->
HTTP/3终端包含QPACK编码器和解码器。
每个终端**必须**启动单个编码器流和解码器流。
接收第二个任意流类型的实例时，**必须**将
其视为类型为HTTP_OWRY_STREAM_COUNT的连接错误。
这些流**必须**关闭。
任何一个单向流类型的关闭都**必须**
被视为HTTP_CLOSED_CRIMARY_STREAM类型的连接错误。

## 编码器指令 {#encoder-instructions}

表更新可以添加表条目，可以使用
现有条目来避免传输冗余信息。
名称可以作为对静态或动态表中
现有条目的引用传输，也可以作为字符常量
传输。对于动态表中已存在的条目，
也可以通过引用使用完整条目，
从而创建重复条目。

本节指定以下编码器说明。

### 插入名称引用

标题字段名称与存储在静态表或动态表
中的条目的标题字段名称相匹配的标题表
中的一个附加项，以“1”位模式开始。
“S”位指示引用是指向静态(S=1)表
还是动态(S=0)表。
下面的6位前缀整数
(参见[RFC7541]第5.1节)用于
定位报头名称的表项。
当S=1时，数字表示静态表索引；
当S=0时，数字是动态表中条目的
相对索引。

报头名称引用后面跟着表示为字符常量的
报头字段值(参见[RFC7541]第5.2节)。

~~~~~~~~~~ drawing
     0   1   2   3   4   5   6   7
   +---+---+---+---+---+---+---+---+
   | 1 | S |    Name Index (6+)    |
   +---+---+-----------------------+
   | H |     Value Length (7+)     |
   +---+---------------------------+
   |  Value String (Length bytes)  |
   +-------------------------------+
~~~~~~~~~~
{: title="Insert Header Field -- Indexed Name"}


### 没有名称引用的情况下插入

在报头表中，报头字段名称和
报头字段值都表示为字符常量(请参见{{primitives}})，
以“01”两位模式开头。

名称表示为6位前缀字符常量，
而值表示为8位前缀字符常量。

~~~~~~~~~~ drawing
     0   1   2   3   4   5   6   7
   +---+---+---+---+---+---+---+---+
   | 0 | 1 | H | Name Length (5+)  |
   +---+---+---+-------------------+
   |  Name String (Length bytes)   |
   +---+---------------------------+
   | H |     Value Length (7+)     |
   +---+---------------------------+
   |  Value String (Length bytes)  |
   +-------------------------------+
~~~~~~~~~~
{: title="Insert Header Field -- New Name"}


### 复制(Duplicate) {#duplicate}

动态表中现有条目的复制以'000'三位字头开始。
现有条目的相对索引表示为具有5位前缀的整数。

~~~~~~~~~~ drawing
     0   1   2   3   4   5   6   7
   +---+---+---+---+---+---+---+---+
   | 0 | 0 | 0 |    Index (5+)     |
   +---+---+---+-------------------+
~~~~~~~~~~
{:#fig-index-with-duplication title="Duplicate"}

现有条目将重新插入动态表中，而不重新发送名称或值。
这对于减少频繁引用的旧条目的驱逐非常有用，既可以避免重新发送标头，也可以避免表中的现有条目有阻止插入新标头的能力。

### 设置动态表容量(Set Dynamic Table Capacity) {#set-dynamic-capacity}

编码器使用以'001'三位字头开始的指令通知解码器动态表容量的变化。
新的动态表容量表示为带有5位前缀的整数（参见[RFC7541]的第5.1节）。

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 0 | 0 | 1 |   Capacity (5+)   |
+---+---+---+-------------------+
~~~~~~~~~~
{:#fig-set-capacity title="Set Dynamic Table Capacity"}

新容量**必须**低于或等于{{maximum-dynamic-table-capacity}}中描述的限制。
在HTTP / 3中，此限制是从解码器中受到的
SETTINGS_QPACK_MAX_TABLE_CAPACITY参数(参考 {{configuration}})的值。
解码器**必须**将超过此限制的新动态表容量值视为类型`HTTP_QPACK_ENCODER_STREAM_ERROR`的连接错误。

减少动态表容量可能导致条目被逐出(参考{{eviction}})。
该操作**禁止**导致具有动态表引用的条目被驱逐(参考 {{reference-tracking}})。
由于此指令未插入条目，因此无法确认更改动态表的容量。


## 解码器指令(Decoder Instructions) {#decoder-instructions}

解码器指令提供用于确保动态表一致性的信息。
它们在解码流中从解码器发送到编码器;
也就是说，服务器通知客户端有关客户端标头块和表更新的处理，客户端通知服务器有关服务器标头块和表更新的处理。

本节指定以下解码器说明。

### 插入计数增量(Insert Count Increment)

插入计数增量指令以'00'两位字头开始。
该指令指定自上一次插入计数增量或标题确认以来增加动态表的已知接收计数，用以得到动态表插入和重复的总数(参考{{known-received-count}})。
Increment字段编码为6位前缀整数。
编码器使用此值来确定哪些表条目可能导致流被阻止，参见{{state-synchronization}}中的描述.

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 0 | 0 |     Increment (6+)    |
+---+---+-----------------------+
~~~~~~~~~~
{:#fig-size-sync title="Insert Count Increment"}

接收增量字段等于零的编码器或一个增加已知接收计数超出
它发送的数量的编码器**必须**被视为类型为“HTTP_QPACK_DECODER_STREAM_ERROR”的连接错误。

### 头确认(Header Acknowledgement)

在处理完其声明的必需插入计数不为零的标题块之后，解码器在解码器流上发出标头确认指令。
该指令以“1”一位字头开始，并包括标题块的相关流ID，编码为7位前缀整数。
对端的编码器使用它来知道何时可以安全地逐出条目，并可能更新已知接收计数。

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 1 |      Stream ID (7+)       |
+---+---------------------------+
~~~~~~~~~~
{:#fig-header-ack title="Header Acknowledgement"}

可以多次识别相同的流ID，因为在中间响应，预告和推送请求的情况下，可以在单个流上发送多个头块。
由于每个流上的HEADERS和PUSH_PROMISE帧会被接收并按顺序处理，因此这给编码器提供了关于流中的哪些报头块已被完全处理的精确反馈。

如果编码器接收到一个头确认指令，该指令指的是已经确认了具有非零必需插入计数的每个头块的流，
则**必须**将其视为类型为“HTTP_QPACK_DECODER_STREAM_ERROR”的连接错误。

当允许阻塞引用时，编码器使用标头块确认来更新已知接收计数。
如果标头块可能阻塞，则确认意味着解码器已经接收到处理标头块所需的所有动态表状态。
如果确认的标头块的必需插入计数大于编码器的当前已知接收计数，则块的必需插入计数将成为新的已知接收计数。

### 流取消(Stream Cancellation)

指令以'01'两位字头开始。
该指令包括受影响流的流ID(请求或推送流)编码为6位前缀整数。

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 0 | 1 |     Stream ID (6+)    |
+---+---+-----------------------+
~~~~~~~~~~
{:#fig-stream-cancel title="Stream Cancellation"}

重置的流可能具有多个具有动态表引用的未完成标头块。
当端点在流结束之前接收到流重置时，它在解码器流上生成流取消指令。
类似地，当端点放弃读取流时，它需要使用流取消指令来发信号通知。
这向编码器发出信号，表明对该流上的动态表的所有引用都不再是未完成的。
最大动态表容量等于零的解码器（参见{{maximum-dynamic-table-capacity}}）可以省略发送流取消，因为编码器不能有任何动态表引用。
编码器无法从该指令推断出已接收到对动态表的任何更新。


## 头部块的指令(Header Block Instructions)

HTTP/3 端会将头部列表转换为头部块，并在HEADERS和PUSH_PROMISE帧
内交换它们。解码器解释头部指令以便构造头部列表。
这些指令引用静态列表或在不修改的情况下引用特定状态的动态列表。

本节指定以下头部块指令。

### 头部块前缀(Header Block Prefix) {#header-prefix}

每个标题块都以两个整数为前缀。必须插入计数（RIC）被编码为一个紧接着
{{ric}}中描述的编码之后的有着8位前缀的整数。
The Base 被编码为可直接取模的有符号整数，利用一个符号位和
有7位前缀的值（请参阅{{base}}）。
这两个值后面是压缩头部的指令，整个块会被使用的协议
分帧．

~~~~~~~~~~  drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
|   Required Insert Count (8+)  |
+---+---------------------------+
| S |      Delta Base (7+)      |
+---+---------------------------+
|      Compressed Headers     ...
+-------------------------------+
~~~~~~~~~~
{:#fig-base-index title="帧载荷"}


#### 必需的插入计数(Required Insert Count) {#ric}

必需的插入计数(ric)标识处理头部块所需的动态表的状态。
块解码器使用必需的插入计数来确定何时可以安全地处理块的其余部分。

编码器在编码之前对必需的插入计数(RIC)转换如下：

~~~
   if ReqInsertCount == 0:
      EncInsertCount = 0
   else:
      EncInsertCount = (ReqInsertCount mod (2 * MaxEntries)) + 1
~~~


这里`MaxEntries`是动态表可以拥有的最大条目数。
最小的条目具有空名称和值字符串，大小为32.因此`MaxEntries`计算为

~~~
   MaxEntries = floor( MaxTableCapacity / 32 )
~~~

`MaxTableCapacity`是解码器指定的动态表的最大容量,见
{{maximum-dynamic-table-capacity}}.

此编码限制了长期连接上的前缀长度。

解码器可以使用诸如以下的算法重建所需的插入计数。如果解码器
遇到无法由符合编码器生成的EncodedInsertCount值，则**必须**将其视为
`HTTP_QPACK_DECOMPRESSION_FAILED`类型的流错误。

TotalNumberOfInserts是解码器动态表中插入的总数。


~~~
   FullRange = 2 * MaxEntries
   if EncodedInsertCount == 0:
      ReqInsertCount = 0
   else:
      if EncodedInsertCount > FullRange:
         Error
      MaxValue = TotalNumberOfInserts + MaxEntries

      # MaxWrapped is the largest possible value of
      # ReqInsertCount that is 0 mod 2*MaxEntries
      MaxWrapped = floor(MaxValue / FullRange) * FullRange
      ReqInsertCount = MaxWrapped + EncodedInsertCount - 1

      # If ReqInsertCount exceeds MaxValue, the Encoder's value
      # must have wrapped one fewer time
      if ReqInsertCount > MaxValue:
         if ReqInsertCount < FullRange:
            Error
         ReqInsertCount -= FullRange
~~~


例如，如果动态表是100个字节，则必需的插入计数将以模6编码。
如果解码器已接收10个插入，则编码值3表示头部块的必需插入计数为9。

#### 基数(Base) {#base}

`Base`用于解析动态表中的引用，见{{relative-indexing}}.

为了节省空间，Base使用一位符号和相对于插入计数的改变量`Delta Base`值进行编
码。符号位为0表示Base大于或等于Insert Count的值;将Delta Base的值
添加到Insert Count以确定Base的值。符号位为1表示Base小于插入计数。
即：

~~~
   if S == 0:
      Base = ReqInsertCount + DeltaBase
   else:
      Base = ReqInsertCount - DeltaBase - 1
~~~

单通道编码器在编码头部块之前确定Base。如果编码器在编码头部块
时在动态表中插入条目，则必需插入计数将大于基数，因此编码的差值为负数，
符号位设置为1.如果头部块未引用在表中的最新条目输入并且未插入任何
新条目，Base将大于Required Insert Count，因此delta将为正且符号
位设置为0。


在编码头部块之前产生表更新的编码器可能会将Required Insert Count
和Base设置为相同的值。在这种情况下，符号位和Delta Base都将设置为零。

不引用动态表的头部块可以设置Base为任何值;
将Delta Base设置为零是最有效的编码。

例如，如果所需插入计数为9，则解码器接收S位为1且Delta Base为2.
这将Base设置为6并为三个条目启用后基索引。在此示例中，
常规索引1表示添加到表中的第5个条目;后基索引为1指的是第8个条目。


### 被索引的标题字段(Indexed Header Field)

被索引标题字段占位符标识静态表或动态表中的条目，并使该标题字段被添
加到解码的标题列表中，如[RFC7541]的第3.2节中所述

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 1 | S |      Index (6+)       |
+---+---+-----------------------+
~~~~~~~~~~
{: title="被索引标题字段"}

如果条目在静态表中，或者在绝对索引小于Base的动态表中,
则该表示以1位数字`1`开始的形式，后跟S位表明引用是否进入静态（ S = 1）
或动态（S = 0）表。最后，匹配头字段的相对索引表示为具有6位前缀
的整数（参见[RFC7541]的第5.1节）。


### 带有后基索引的索引标题字段(Indexed Header Field With Post-Base Index)

如果条目在绝对索引大于或等于Base的动态表中，
表现为'0001'4位模式开始，后跟匹配的后基索引（参见{{post-base}})
的头部字段，表示为具有4位前缀的整数（参见[RFC7541]的第5.1节）。

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 0 | 0 | 0 | 1 |  Index (4+)   |
+---+---+---+---+---------------+
~~~~~~~~~~
{: title="带有后基索引的头部索引字段"}


### 具有名称引用的文本标头字段(Literal Header Field With Name Reference)

具有名称引用的文本标头字段表示标头字段名称与存储在静态表或动态表中的条目的标头字段名称
相匹配的标头。

如果条目位于静态表或动态表中，且绝对索引小于基准，则此表示以‘01’两位模式开始。如果该条
目位于动态表中，且绝对索引大于或等于基准，则表示将以“0000”四位模式开始。

下一位‘N’表示是否允许中间件在后续跃点上将此标头添加到动态标头表。 当'N'位置位时，编码头
必须始终用文字表示法编码。 特别是，当对等体发送它接收的头字段表示为带有'N'位设置的文字
头字段时，它必须使用文字表示来转发该头字段。 该位用于通过压缩来保护不存在风险的头字段值
（更多详细信息，请参见[RFC7541]的第7.1节）。

~~~~~~~~~~ drawing
     0   1   2   3   4   5   6   7
   +---+---+---+---+---+---+---+---+
   | 0 | 1 | N | S |Name Index (4+)|
   +---+---+---+---+---------------+
   | H |     Value Length (7+)     |
   +---+---------------------------+
   |  Value String (Length bytes)  |
   +-------------------------------+
~~~~~~~~~~
{: title="具有名称引用的文本标头字段"}

对于静态表或动态表中绝对索引小于基准的条目，标头字段名称使用该条目的相对索引表示，该索
引表示为具有4位前缀的整数(参见[RFC7541]的5.1节)。S位指示引用是静态(S=1)还是动态(S=0)表。

### 具有后基准名称引用的文本标头字段(Literal Header Field With Post-Base Name Reference)


对于动态表中绝对索引大于或等于基准的条目，标头字段名称使用该条目的后基准索引
(参见{{post-base}})表示，该索引被编码为具有3位前缀的整数。

~~~~~~~~~~ drawing
     0   1   2   3   4   5   6   7
   +---+---+---+---+---+---+---+---+
   | 0 | 0 | 0 | 0 | N |NameIdx(3+)|
   +---+---+---+---+---+-----------+
   | H |     Value Length (7+)     |
   +---+---------------------------+
   |  Value String (Length bytes)  |
   +-------------------------------+
~~~~~~~~~~
{: title="具有后基准名称引用的文本标头字段"}


### 无名称引用的文字标题字段(Literal Header Field Without Name Reference)

对头表的添加，其中标头字段名称和标头字段值均表示为字符串文字(参见4.1节)，以‘001’三位模式开始。

第四位‘N’指示是否允许中间件在后续跃点上将该报头添加到动态报头表中。设置“N”位时，编码的标头**必须**
始终使用文字表示进行编码。特别地，当对等发送其接收到的表示为设置了“N”位的文字报头字段的报头
字段时，它必须使用文字表示来转发该报头字段。此位用于通过压缩来保护不会被置于风险中的标头字段值
(有关更多详细信息，请参见[RFC7541]的7.1节)。

名称表示为4位前缀字符串文字，而值表示为8位前缀字符串文字。

~~~~~~~~~~ drawing
     0   1   2   3   4   5   6   7
   +---+---+---+---+---+---+---+---+
   | 0 | 0 | 1 | N | H |NameLen(3+)|
   +---+---+---+---+---+-----------+
   |  Name String (Length bytes)   |
   +---+---------------------------+
   | H |     Value Length (7+)     |
   +---+---------------------------+
   |  Value String (Length bytes)  |
   +-------------------------------+
~~~~~~~~~~
{: title="无名称引用的文字标题字段"}


#  配置(Configuration)

QPACK定义了HTTP/3设置帧中包含的两个设置。

  SETTINGS_QPACK_MAX_TABLE_CAPACITY (0x1):
  : 最大值为2^30-1的整数。默认值为零字节。有关用法，请参阅{{table-dynamic}}。这相当于HTTP/2中
    的SETINGS_HEADER_TABLE_SIZE。

  SETTINGS_QPACK_BLOCKED_STREAMS (0x7):
  : 最大值为2^16-1的整数。默认值为零。参见{{overview-hol-avoidance}}。


# 错误处理(Error Handling) {#error-handling}

HTTP/3中QPACK里的中止流与连接的故障可以通过如下错误代码表示：

HTTP_QPACK_DECOMPRESSION_FAILED (TBD):
: 解码器无法解释报头块指令，且不能继续解码该报头块。

HTTP_QPACK_ENCODER_STREAM_ERROR (TBD):
: 解码器无法解释在编码器流上接收的编码器指令。

HTTP_QPACK_DECODER_STREAM_ERROR (TBD):
: 编码器无法解释在解码器流上接收的解码器指令。


在遇到错误时，实现**可以**选择将其视为连接错误，即使该文档规定**必须**将其视为流错误。


# Security Considerations

TBD.

# IANA Considerations

## Settings Registration

This document specifies two settings. The entries in the following table are
registered in the "HTTP/3 Settings" registry established in {{HTTP3}}.

|------------------------------|--------|---------------------------|
| Setting Name                 | Code   | Specification             |
| ---------------------------- | :----: | ------------------------- |
| QPACK_MAX_TABLE_CAPACITY     | 0x1    | {{configuration}}         |
| QPACK_BLOCKED_STREAMS        | 0x7    | {{configuration}}         |
| ---------------------------- | ------ | ------------------------- |

## Stream Type Registration

This document specifies two stream types. The entries in the following table are
registered in the "HTTP/3 Stream Type" registry established in {{HTTP3}}.

| ---------------------------- | ------ | ------------------------- | ------ |
| Stream Type                  | Code   | Specification             | Sender |
| ---------------------------- | :----: | ------------------------- | ------ |
| QPACK Encoder Stream         | 0x02   | {{wire-format}}           | Both   |
| QPACK Decoder Stream         | 0x03   | {{wire-format}}           | Both   |
| ---------------------------- | ------ | ------------------------- | ------ |

## Error Code Registration

This document specifies three error codes. The entries in the following table
are registered in the "HTTP/3 Error Code" registry established in {{HTTP3}}.

| --------------------------------- | ----- | ---------------------------------------- | ---------------------- |
| Name                              | Code  | Description                              | Specification          |
| --------------------------------- | ----- | ---------------------------------------- | ---------------------- |
| HTTP_QPACK_DECOMPRESSION_FAILED   | TBD   | Decompression of a header block failed   | {{error-handling}}     |
| HTTP_QPACK_ENCODER_STREAM_ERROR   | TBD   | Error on the encoder stream              | {{error-handling}}     |
| HTTP_QPACK_DECODER_STREAM_ERROR   | TBD   | Error on the decoder stream              | {{error-handling}}     |
| --------------------------------- | ----- | ---------------------------------------- | ---------------------- |


--- back

# Static Table

| Index | Name                             | Value                                                       |
| ----- | -------------------------------- | ----------------------------------------------------------- |
| 0     | :authority                       |                                                             |
| 1     | :path                            | /                                                           |
| 2     | age                              | 0                                                           |
| 3     | content-disposition              |                                                             |
| 4     | content-length                   | 0                                                           |
| 5     | cookie                           |                                                             |
| 6     | date                             |                                                             |
| 7     | etag                             |                                                             |
| 8     | if-modified-since                |                                                             |
| 9     | if-none-match                    |                                                             |
| 10    | last-modified                    |                                                             |
| 11    | link                             |                                                             |
| 12    | location                         |                                                             |
| 13    | referer                          |                                                             |
| 14    | set-cookie                       |                                                             |
| 15    | :method                          | CONNECT                                                     |
| 16    | :method                          | DELETE                                                      |
| 17    | :method                          | GET                                                         |
| 18    | :method                          | HEAD                                                        |
| 19    | :method                          | OPTIONS                                                     |
| 20    | :method                          | POST                                                        |
| 21    | :method                          | PUT                                                         |
| 22    | :scheme                          | http                                                        |
| 23    | :scheme                          | https                                                       |
| 24    | :status                          | 103                                                         |
| 25    | :status                          | 200                                                         |
| 26    | :status                          | 304                                                         |
| 27    | :status                          | 404                                                         |
| 28    | :status                          | 503                                                         |
| 29    | accept                           | \*/\*                                                       |
| 30    | accept                           | application/dns-message                                     |
| 31    | accept-encoding                  | gzip, deflate, br                                           |
| 32    | accept-ranges                    | bytes                                                       |
| 33    | access-control-allow-headers     | cache-control                                               |
| 34    | access-control-allow-headers     | content-type                                                |
| 35    | access-control-allow-origin      | \*                                                          |
| 36    | cache-control                    | max-age=0                                                   |
| 37    | cache-control                    | max-age=2592000                                             |
| 38    | cache-control                    | max-age=604800                                              |
| 39    | cache-control                    | no-cache                                                    |
| 40    | cache-control                    | no-store                                                    |
| 41    | cache-control                    | public, max-age=31536000                                    |
| 42    | content-encoding                 | br                                                          |
| 43    | content-encoding                 | gzip                                                        |
| 44    | content-type                     | application/dns-message                                     |
| 45    | content-type                     | application/javascript                                      |
| 46    | content-type                     | application/json                                            |
| 47    | content-type                     | application/x-www-form-urlencoded                           |
| 48    | content-type                     | image/gif                                                   |
| 49    | content-type                     | image/jpeg                                                  |
| 50    | content-type                     | image/png                                                   |
| 51    | content-type                     | text/css                                                    |
| 52    | content-type                     | text/html; charset=utf-8                                    |
| 53    | content-type                     | text/plain                                                  |
| 54    | content-type                     | text/plain;charset=utf-8                                    |
| 55    | range                            | bytes=0-                                                    |
| 56    | strict-transport-security        | max-age=31536000                                            |
| 57    | strict-transport-security        | max-age=31536000; includesubdomains                         |
| 58    | strict-transport-security        | max-age=31536000; includesubdomains; preload                |
| 59    | vary                             | accept-encoding                                             |
| 60    | vary                             | origin                                                      |
| 61    | x-content-type-options           | nosniff                                                     |
| 62    | x-xss-protection                 | 1; mode=block                                               |
| 63    | :status                          | 100                                                         |
| 64    | :status                          | 204                                                         |
| 65    | :status                          | 206                                                         |
| 66    | :status                          | 302                                                         |
| 67    | :status                          | 400                                                         |
| 68    | :status                          | 403                                                         |
| 69    | :status                          | 421                                                         |
| 70    | :status                          | 425                                                         |
| 71    | :status                          | 500                                                         |
| 72    | accept-language                  |                                                             |
| 73    | access-control-allow-credentials | FALSE                                                       |
| 74    | access-control-allow-credentials | TRUE                                                        |
| 75    | access-control-allow-headers     | \*                                                          |
| 76    | access-control-allow-methods     | get                                                         |
| 77    | access-control-allow-methods     | get, post, options                                          |
| 78    | access-control-allow-methods     | options                                                     |
| 79    | access-control-expose-headers    | content-length                                              |
| 80    | access-control-request-headers   | content-type                                                |
| 81    | access-control-request-method    | get                                                         |
| 82    | access-control-request-method    | post                                                        |
| 83    | alt-svc                          | clear                                                       |
| 84    | authorization                    |                                                             |
| 85    | content-security-policy          | script-src \'none\'; object-src \'none\'; base-uri \'none\' |
| 86    | early-data                       | 1                                                           |
| 87    | expect-ct                        |                                                             |
| 88    | forwarded                        |                                                             |
| 89    | if-range                         |                                                             |
| 90    | origin                           |                                                             |
| 91    | purpose                          | prefetch                                                    |
| 92    | server                           |                                                             |
| 93    | timing-allow-origin              | \*                                                          |
| 94    | upgrade-insecure-requests        | 1                                                           |
| 95    | user-agent                       |                                                             |
| 96    | x-forwarded-for                  |                                                             |
| 97    | x-frame-options                  | deny                                                        |
| 98    | x-frame-options                  | sameorigin                                                  |

# Sample One Pass Encoding Algorithm

Pseudo-code for single pass encoding, excluding handling of duplicates,
non-blocking mode, and reference tracking.

~~~
baseIndex = dynamicTable.baseIndex
largestReference = 0
for header in headers:
  staticIdx = staticTable.getIndex(header)
  if staticIdx:
    encodeIndexReference(streamBuffer, staticIdx)
    continue

  dynamicIdx = dynamicTable.getIndex(header)
  if !dynamicIdx:
    # No matching entry.  Either insert+index or encode literal
    nameIdx = getNameIndex(header)
    if shouldIndex(header) and dynamicTable.canIndex(header):
      encodeLiteralWithIncrementalIndex(controlBuffer, nameIdx,
                                        header)
      dynamicTable.add(header)
      dynamicIdx = dynamicTable.baseIndex

  if !dynamicIdx:
    # Couldn't index it, literal
    if nameIdx <= staticTable.size:
      encodeLiteral(streamBuffer, nameIndex, header)
    else:
      # encode literal, possibly with nameIdx above baseIndex
      encodeDynamicLiteral(streamBuffer, nameIndex, baseIndex,
                           header)
      largestReference = max(largestReference,
                             dynamicTable.toAbsolute(nameIdx))
  else:
    # Dynamic index reference
    assert(dynamicIdx)
    largestReference = max(largestReference, dynamicIdx)
    # Encode dynamicIdx, possibly with dynamicIdx above baseIndex
    encodeDynamicIndexReference(streamBuffer, dynamicIdx,
                                baseIndex)

# encode the prefix
encodeInteger(prefixBuffer, 0x00, largestReference, 8)
if baseIndex >= largestReference:
  encodeInteger(prefixBuffer, 0, baseIndex - largestReference, 7)
else:
  encodeInteger(prefixBuffer, 0x80,
                largestReference  - baseIndex, 7)

return controlBuffer, prefixBuffer + streamBuffer
~~~

# Change Log

> **RFC Editor's Note:** Please remove this section prior to publication of a
> final version of this document.

## Since draft-ietf-quic-qpack-05

- Introduced the terms dynamic table capacity and maximum dynamic table
  capacity.
- Renamed SETTINGS_HEADER_TABLE_SIZE to SETTINGS_QPACK_MAX_TABLE_CAPACITY.

## Since draft-ietf-quic-qpack-04

- Changed calculation of Delta Base Index to avoid an illegal value (#2002,
  #2005)

## Since draft-ietf-quic-qpack-03

- Change HTTP settings defaults (#2038)
- Substantial editorial reorganization

## Since draft-ietf-quic-qpack-02

- Largest Reference encoded modulo MaxEntries (#1763)
- New Static Table (#1355)
- Table Size Update with Insert Count=0 is a connection error (#1762)
- Stream Cancellations are optional when SETTINGS_HEADER_TABLE_SIZE=0 (#1761)
- Implementations must handle 62 bit integers (#1760)
- Different error types for each QPACK stream, other changes to error
  handling (#1726)
- Preserve header field order (#1725)
- Initial table size is the maximum permitted when table is first usable (#1642)

## Since draft-ietf-quic-qpack-01

- Only header blocks that reference the dynamic table are acknowledged (#1603,
  #1605)

## Since draft-ietf-quic-qpack-00

- Renumbered instructions for consistency (#1471, #1472)
- Decoder is allowed to validate largest reference (#1404, #1469)
- Header block acknowledgments also acknowledge the associated largest reference
  (#1370, #1400)
- Added an acknowledgment for unread streams (#1371, #1400)
- Removed framing from encoder stream (#1361,#1467)
- Control streams use typed unidirectional streams rather than fixed stream IDs
  (#910,#1359)

## Since draft-ietf-quic-qcram-00

- Separate instruction sets for table updates and header blocks (#1235, #1142,
  #1141)
- Reworked indexing scheme (#1176, #1145, #1136, #1130, #1125, #1314)
- Added mechanisms that support one-pass encoding (#1138, #1320)
- Added a setting to control the number of blocked decoders (#238, #1140, #1143)
- Moved table updates and acknowledgments to dedicated streams (#1121, #1122,
  #1238)

# Acknowledgments
{:numbered="false"}

This draft draws heavily on the text of {{!RFC7541}}.  The indirect input of
those authors is gratefully acknowledged, as well as ideas from:

* Ryan Hamilton

* Patrick McManus

* Kazuho Oku

* Biren Roy

* Ian Swett

* Dmitri Tikhonov

Buck's contribution was supported by Google during his employment there.

A substantial portion of Mike's contribution was supported by Microsoft during
his employment there.
