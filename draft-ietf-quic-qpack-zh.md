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

QPACK 重新使用了 HPACK 的核心概念，但经过重新设计，在针对队头阻塞的恢复能力和最佳压缩比做平衡，允许在出现无序交付的情况下保持正确性，具有实现的灵活性。
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

# Compression Process Overview

Like HPACK, QPACK uses two tables for associating header fields to indices.  The
static table (see {{table-static}}) is predefined and contains common header
fields (some of them with an empty value).  The dynamic table (see
{{table-dynamic}}) is built up over the course of the connection and can be used
by the encoder to index header fields in the encoded header lists.

QPACK instructions appear in three different types of streams:

- The encoder uses a unidirectional stream to modify the state of the dynamic
table without emitting header fields associated with any particular request.

- HEADERS and PUSH_PROMISE frames on request and push streams reference the
table state without modifying it.

- The decoder sends feedback to the encoder on a unidirectional stream.  This
feedback enables the encoder to manage dynamic table state.

## Encoder

An encoder compresses a header list by emitting either an indexed or a literal
representation for each header field in the list.  References to the static
table and literal representations do not require any dynamic state and never
risk head-of-line blocking.  References to the dynamic table risk head-of-line
blocking if the encoder has not received an acknowledgement indicating the entry
is available at the decoder.

An encoder MAY insert any entry in the dynamic table it chooses; it is not
limited to header fields it is compressing.

QPACK preserves the ordering of header fields within each header list.  An
encoder MUST emit header field representations in the order they appear in the
input header list.

QPACK is designed to contain the more complex state tracking to the encoder,
while the decoder is relatively simple.

### Reference Tracking

An encoder MUST ensure that a header block which references a dynamic table
entry is not received by the decoder after the referenced entry has been
evicted.  Hence the encoder needs to track information about each compressed
header block that references the dynamic table until that header block is
acknowledged by the decoder.

### Blocked Dynamic Table Insertions {#blocked-insertion}

An encoder MUST NOT insert an entry into the dynamic table (or duplicate an
existing entry) if doing so would evict an entry with unacknowledged references.
For header blocks that might rely on the newly added entry, the encoder can use
a literal representation.

To ensure that the encoder is not prevented from adding new entries, the encoder
can avoid referencing entries that are close to eviction.  Rather than
reference such an entry, the encoder can emit a Duplicate instruction (see
{{duplicate}}), and reference the duplicate instead.

Determining which entries are too close to eviction to reference is an encoder
preference.  One heuristic is to target a fixed amount of available space in the
dynamic table: either unused space or space that can be reclaimed by evicting
unreferenced entries.  To achieve this, the encoder can maintain a draining
index, which is the smallest absolute index in the dynamic table that it will
emit a reference for.  As new entries are inserted, the encoder increases the
draining index to maintain the section of the table that it will not reference.
If the encoder does not create new references to entries with an absolute index
lower than the draining index, the number of unacknowledged references to those
entries will eventually become zero, allowing them to be evicted.

~~~~~~~~~~  drawing
   +----------+---------------------------------+--------+
   | Draining |          Referenceable          | Unused |
   | Entries  |             Entries             | Space  |
   +----------+---------------------------------+--------+
   ^          ^                                 ^
   |          |                                 |
 Dropping    Draining Index               Insertion Point
  Point
~~~~~~~~~~
{:#fig-draining-index title="Draining Dynamic Table Entries"}


### Avoiding Head-of-Line Blocking {#overview-hol-avoidance}

Because QUIC does not guarantee order between data on different streams, a
header block might reference an entry in the dynamic table that has not yet been
received.

Each header block contains a Required Insert Count, the lowest possible value
for the Insert Count with which the header block can be decoded. For a header
block with references to the dynamic table, the Required Insert Count is one
larger than the largest Absolute Index of all referenced dynamic table
entries. For a header block with no references to the dynamic table, the
Required Insert Count is zero.

If the decoder encounters a header block with a Required Insert Count value
larger than defined above, it MAY treat this as a stream error of type
HTTP_QPACK_DECOMPRESSION_FAILED.  If the decoder encounters a header block with
a Required Insert Count value smaller than defined above, it MUST treat this as
a stream error of type HTTP_QPACK_DECOMPRESSION_FAILED as prescribed in
{{invalid-references}}.

When the Required Insert Count is zero, the frame contains no references to the
dynamic table and can always be processed immediately.

If the Required Insert Count is greater than the number of dynamic table entries
received, the stream is considered "blocked."  While blocked, header field data
SHOULD remain in the blocked stream's flow control window.  A stream becomes
unblocked when the Insert Count becomes greater than or equal to the Required
Insert Count for all header blocks the decoder has started reading from the
stream.

The SETTINGS_QPACK_BLOCKED_STREAMS setting (see {{configuration}}) specifies an
upper bound on the number of streams which can be blocked. An encoder MUST limit
the number of streams which could become blocked to the value of
SETTINGS_QPACK_BLOCKED_STREAMS at all times. Note that the decoder might not
actually become blocked on every stream which risks becoming blocked.  If the
decoder encounters more blocked streams than it promised to support, it MUST
treat this as a stream error of type HTTP_QPACK_DECOMPRESSION_FAILED.

An encoder can decide whether to risk having a stream become blocked. If
permitted by the value of SETTINGS_QPACK_BLOCKED_STREAMS, compression efficiency
can often be improved by referencing dynamic table entries that are still in
transit, but if there is loss or reordering the stream can become blocked at the
decoder.  An encoder avoids the risk of blocking by only referencing dynamic
table entries which have been acknowledged, but this could mean using
literals. Since literals make the header block larger, this can result in the
encoder becoming blocked on congestion or flow control limits.

### Known Received Count

In order to identify which dynamic table entries can be safely used without a
stream becoming blocked, the encoder tracks the number of entries received by
the decoder.  The Known Received Count tracks the total number of acknowledged
insertions.

When blocking references are permitted, the encoder uses header block
acknowledgement to maintain the Known Received Count, as described in
{{header-acknowledgement}}.

To acknowledge dynamic table entries which are not referenced by header blocks,
for example because the encoder or the decoder have chosen not to risk blocked
streams, the decoder sends an Insert Count Increment instruction (see
{{insert-count-increment}}).


## Decoder

As in HPACK, the decoder processes header blocks and emits the corresponding
header lists. It also processes dynamic table modifications from encoder
instructions received on the encoder stream.

The decoder MUST emit header fields in the order their representations appear in
the input header block.


### State Synchronization

The decoder instructions ({{decoder-instructions}}) signal key events at the
decoder that permit the encoder to track the decoder's state.  These events are:

- Complete processing of a header block
- Abandonment of a stream which might have remaining header blocks
- Receipt of new dynamic table entries

Knowledge that a header block with references to the dynamic table has been
processed permits the encoder to evict entries to which no unacknowledged
references remain, regardless of whether those references were potentially
blocking (see {{blocked-insertion}}).  When a stream is reset or abandoned, the
indication that these header blocks will never be processed serves a similar
function; see {{stream-cancellation}}.

The decoder chooses when to emit Insert Count Increment instructions (see
{{insert-count-increment}}). Emitting an instruction after adding each new
dynamic table entry will provide the most timely feedback to the encoder, but
could be redundant with other decoder feedback. By delaying an Insert Count
Increment instruction, the decoder might be able to coalesce multiple Insert
Count Increment instructions, or replace them entirely with Header
Acknowledgements (see {{header-acknowledgement}}). However, delaying too long
may lead to compression inefficiencies if the encoder waits for an entry to be
acknowledged before using it.

### Blocked Decoding

To track blocked streams, the Required Insert Count value for each stream can be
used.  Whenever the decoder processes a table update, it can begin decoding any
blocked streams that now have their dependencies satisfied.


# Header Tables

Unlike in HPACK, entries in the QPACK static and dynamic tables are addressed
separately.  The following sections describe how entries in each table are
addressed.

## Static Table {#table-static}

The static table consists of a predefined static list of header fields, each of
which has a fixed index over time.  Its entries are defined in {{static-table}}.

Note the QPACK static table is indexed from 0, whereas the HPACK static table
is indexed from 1.

When the decoder encounters an invalid static table index in a header block
instruction it MUST treat this as a stream error of type
`HTTP_QPACK_DECOMPRESSION_FAILED`.  If this index is received on the encoder
stream, this MUST be treated as a connection error of type
`HTTP_QPACK_ENCODER_STREAM_ERROR`.

## Dynamic Table {#table-dynamic}

The dynamic table consists of a list of header fields maintained in first-in,
first-out order. Each HTTP/3 endpoint holds a dynamic table that is initially
empty.  Entries are added by encoder instructions received on the encoder stream
(see {{encoder-instructions}}).

The dynamic table can contain duplicate entries (i.e., entries with the same
name and same value).  Therefore, duplicate entries MUST NOT be treated as an
error by the decoder.


### Dynamic Table Size

The size of the dynamic table is the sum of the size of its entries.

The size of an entry is the sum of its name's length in bytes (as defined in
{{string-literals}}), its value's length in bytes, and 32.

The size of an entry is calculated using the length of its name and value
without Huffman encoding applied.


### Dynamic Table Capacity and Eviction {#eviction}

The encoder sets the capacity of the dynamic table, which serves as the upper
limit on its size.  The initial capcity of the dynamic table is zero.

Before a new entry is added to the dynamic table, entries are evicted from the
end of the dynamic table until the size of the dynamic table is less than or
equal to (table capacity - size of new entry) or until the table is empty. The
encoder MUST NOT evict a dynamic table entry unless it has first been
acknowledged by the decoder.

If the size of the new entry is less than or equal to the dynamic table
capacity, then that entry is added to the table.  It is an error if the encoder
attempts to add an entry that is larger than the dynamic table capacity; the
decoder MUST treat this as a connection error of type
`HTTP_QPACK_ENCODER_STREAM_ERROR`.

A new entry can reference an entry in the dynamic table that will be evicted
when adding this new entry into the dynamic table.  Implementations are
cautioned to avoid deleting the referenced name or value if the referenced entry
is evicted from the dynamic table prior to inserting the new entry.

Whenever the dynamic table capacity is reduced by the encoder, entries are
evicted from the end of the dynamic table until the size of the dynamic table is
less than or equal to the new table capacity.  This mechanism can be used to
completely clear entries from the dynamic table by setting a capacity of 0,
which can subsequently be restored.


### Maximum Dynamic Table Capacity

To bound the memory requirements of the decoder, the decoder limits the maximum
value the encoder is permitted to set for the dynamic table capacity.  In
HTTP/3, this limit is determined by the value of
SETTINGS_QPACK_MAX_TABLE_CAPACITY sent by the decoder (see {{configuration}}).
The encoder MUST not set a dynamic table capacity that exceeds this maximum, but
it can choose to use a lower dynamic table capacity (see
{{set-dynamic-capacity}}).

For clients using 0-RTT data in HTTP/3, the server's maximum table capacity is
the remembered value of the setting, or zero if the value was not previously
sent.  When the client's 0-RTT value of the SETTING is 0, the server MAY set it
to a non-zero value in its SETTINGS frame. If the remembered value is non-zero,
the server MUST send the same non-zero value in its SETTINGS frame.  If it
specifies any other value, or omits SETTINGS_QPACK_MAX_TABLE_CAPACITY from
SETTINGS, the encoder must treat this as a connection error of type
`HTTP_QPACK_DECODER_STREAM_ERROR`.

For HTTP/3 servers and HTTP/3 clients when 0-RTT is not attempted or is
rejected, the maximum table capacity is 0 until the encoder processes a SETTINGS
frame with a non-zero value of SETTINGS_QPACK_MAX_TABLE_CAPACITY.

When the maximum table capacity is 0, the encoder MUST NOT insert entries into
the dynamic table, and MUST NOT send any encoder instructions on the encoder
stream.


### Absolute Indexing {#indexing}

Each entry possesses both an absolute index which is fixed for the lifetime of
that entry and a relative index which changes based on the context of the
reference. The first entry inserted has an absolute index of "0"; indices
increase by one with each insertion.


### Relative Indexing

The relative index begins at zero and increases in the opposite direction from
the absolute index.  Determining which entry has a relative index of "0" depends
on the context of the reference.

In encoder instructions, a relative index of "0" always refers to the most
recently inserted value in the dynamic table.  Note that this means the entry
referenced by a given relative index will change while interpreting instructions
on the encoder stream.

~~~~~ drawing
      +-----+---------------+-------+
      | n-1 |      ...      |   d   |  Absolute Index
      + - - +---------------+ - - - +
      |  0  |      ...      | n-d-1 |  Relative Index
      +-----+---------------+-------+
      ^                             |
      |                             V
Insertion Point               Dropping Point

n = count of entries inserted
d = count of entries dropped
~~~~~
{: title="Example Dynamic Table Indexing - Control Stream"}

Unlike encoder instructions, relative indices in header block instructions are
relative to the Base at the beginning of the header block (see
{{header-prefix}}). This ensures that references are stable even if the dynamic
table is updated while decoding a header block.

The Base is encoded as a value relative to the Required Insert Count. The Base
identifies which dynamic table entries can be referenced using relative
indexing, starting with 0 at the last entry added.

Post-Base references are used for entries inserted after base, starting at 0 for
the first entry added after the Base, see {{post-base}}.

~~~~~ drawing
 Required
  Insert
  Count        Base
    |           |
    V           V
    +-----+-----+-----+-----+-------+
    | n-1 | n-2 | n-3 | ... |   d   |  Absolute Index
    +-----+-----+  -  +-----+   -   +
                |  0  | ... | n-d-3 |  Relative Index
                +-----+-----+-------+

n = count of entries inserted
d = count of entries dropped
~~~~~
{: title="Example Dynamic Table Indexing - Relative Index in Header Block"}


### Post-Base索引 {#post-base}

报头块可以引用在Base标识的条目之后添加的条目。
这允许编码器在一次传输中处理报头块，
并包含对在处理此(或其他)报头块时添加的条目的引用。
使用Post-Base指令引用新添加的条目。
Post-base指令的指数与绝对指数的增长方向相同，
零值是在Base之后插入的第一个条目。

~~~~~ drawing
               Base
                |
                V
    +-----+-----+-----+-----+-----+
    | n-1 | n-2 | n-3 | ... |  d  |  Absolute Index
    +-----+-----+-----+-----+-----+
    |  1  |  0  |                    Post-Base Index
    +-----+-----+

n = count of entries inserted
d = count of entries dropped
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


### Duplicate {#duplicate}

Duplication of an existing entry in the dynamic table starts with the '000'
three-bit pattern.  The relative index of the existing entry is represented as
an integer with a 5-bit prefix.

~~~~~~~~~~ drawing
     0   1   2   3   4   5   6   7
   +---+---+---+---+---+---+---+---+
   | 0 | 0 | 0 |    Index (5+)     |
   +---+---+---+-------------------+
~~~~~~~~~~
{:#fig-index-with-duplication title="Duplicate"}

The existing entry is re-inserted into the dynamic table without resending
either the name or the value. This is useful to mitigate the eviction of older
entries which are frequently referenced, both to avoid the need to resend the
header and to avoid the entry in the table blocking the ability to insert new
headers.

### Set Dynamic Table Capacity {#set-dynamic-capacity}

An encoder informs the decoder of a change to the dynamic table capacity using
an instruction which begins with the '001' three-bit pattern.  The new dynamic
table capacity is represented as an integer with a 5-bit prefix (see Section 5.1
of [RFC7541]).

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 0 | 0 | 1 |   Capacity (5+)   |
+---+---+---+-------------------+
~~~~~~~~~~
{:#fig-set-capacity title="Set Dynamic Table Capacity"}

The new capacity MUST be lower than or equal to the limit described in
{{maximum-dynamic-table-capacity}}.  In HTTP/3, this limit is the value of the
SETTINGS_QPACK_MAX_TABLE_CAPACITY parameter (see {{configuration}}) received
from the decoder.  The decoder MUST treat a new dynamic table capacity value
that exceeds this limit as a connection error of type
`HTTP_QPACK_ENCODER_STREAM_ERROR`.

Reducing the dynamic table capacity can cause entries to be evicted (see
{{eviction}}).  This MUST NOT cause the eviction of entries with outstanding
references (see {{reference-tracking}}).  Changing the capacity of the dynamic
table is not acknowledged as this instruction does not insert an entry.


## Decoder Instructions {#decoder-instructions}

Decoder instructions provide information used to ensure consistency of the
dynamic table. They are sent from the decoder to the encoder on a decoder
stream; that is, the server informs the client about the processing of the
client's header blocks and table updates, and the client informs the server
about the processing of the server's header blocks and table updates.

This section specifies the following decoder instructions.

### Insert Count Increment

The Insert Count Increment instruction begins with the '00' two-bit pattern.
The instruction specifies the total number of dynamic table inserts and
duplications since the last Insert Count Increment or Header Acknowledgement
that increased the Known Received Count for the dynamic table (see
{{known-received-count}}).  The Increment field is encoded as a 6-bit prefix
integer. The encoder uses this value to determine which table entries might
cause a stream to become blocked, as described in {{state-synchronization}}.

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 0 | 0 |     Increment (6+)    |
+---+---+-----------------------+
~~~~~~~~~~
{:#fig-size-sync title="Insert Count Increment"}

An encoder that receives an Increment field equal to zero or one that increases
the Known Received Count beyond what the encoder has sent MUST treat this as a
connection error of type `HTTP_QPACK_DECODER_STREAM_ERROR`.

### Header Acknowledgement

After processing a header block whose declared Required Insert Count is not
zero, the decoder emits a Header Acknowledgement instruction on the decoder
stream.  The instruction begins with the '1' one-bit pattern and includes the
header block's associated stream ID, encoded as a 7-bit prefix integer.  It is
used by the peer's encoder to know when it is safe to evict an entry, and
possibly update the Known Received Count.

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 1 |      Stream ID (7+)       |
+---+---------------------------+
~~~~~~~~~~
{:#fig-header-ack title="Header Acknowledgement"}

The same Stream ID can be identified multiple times, as multiple header blocks
can be sent on a single stream in the case of intermediate responses, trailers,
and pushed requests.  Since HEADERS and PUSH_PROMISE frames on each stream are
received and processed in order, this gives the encoder precise feedback on
which header blocks within a stream have been fully processed.

If an encoder receives a Header Acknowledgement instruction referring to a
stream on which every header block with a non-zero Required Insert Count has
already been acknowledged, that MUST be treated as a connection error of type
`HTTP_QPACK_DECODER_STREAM_ERROR`.

When blocking references are permitted, the encoder uses acknowledgement of
header blocks to update the Known Received Count.  If a header block was
potentially blocking, the acknowledgement implies that the decoder has received
all dynamic table state necessary to process the header block.  If the Required
Insert Count of an acknowledged header block was greater than the encoder's
current Known Received Count, the block's Required Insert Count becomes the new
Known Received Count.


### Stream Cancellation

The instruction begins with the '01' two-bit pattern. The instruction includes
the stream ID of the affected stream - a request or push stream - encoded as a
6-bit prefix integer.

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 0 | 1 |     Stream ID (6+)    |
+---+---+-----------------------+
~~~~~~~~~~
{:#fig-stream-cancel title="Stream Cancellation"}

A stream that is reset might have multiple outstanding header blocks with
dynamic table references.  When an endpoint receives a stream reset before the
end of a stream, it generates a Stream Cancellation instruction on the decoder
stream.  Similarly, when an endpoint abandons reading of a stream it needs to
signal this using the Stream Cancellation instruction.  This signals to the
encoder that all references to the dynamic table on that stream are no longer
outstanding.  A decoder with a maximum dynamic table capacity equal to zero (see
{{maximum-dynamic-table-capacity}}) MAY omit sending Stream Cancellations,
because the encoder cannot have any dynamic table references.

An encoder cannot infer from this instruction that any updates to the dynamic
table have been received.


## Header Block Instructions

HTTP/3 endpoints convert header lists to headers blocks and exchange them inside
HEADERS and PUSH_PROMISE frames. A decoder interprets header block instructions
in order to construct a header list. These instructions reference the static
table, or dynamic table in a particular state without modifying it.

This section specifies the following header block instructions.

### Header Block Prefix {#header-prefix}

Each header block is prefixed with two integers.  The Required Insert Count is
encoded as an integer with an 8-bit prefix after the encoding described in
{{ric}}).  The Base is encoded as sign-and-modulus integer, using a single sign
bit and a value with a 7-bit prefix (see {{base}}).

These two values are followed by instructions for compressed headers.  The
entire block is expected to be framed by the using protocol.

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
{:#fig-base-index title="Frame Payload"}


#### Required Insert Count {#ric}

Required Insert Count identifies the state of the dynamic table needed to
process the header block.  Blocking decoders use the Required Insert Count to
determine when it is safe to process the rest of the block.

The encoder transforms the Required Insert Count as follows before encoding:

~~~
   if ReqInsertCount == 0:
      EncInsertCount = 0
   else:
      EncInsertCount = (ReqInsertCount mod (2 * MaxEntries)) + 1
~~~

Here `MaxEntries` is the maximum number of entries that the dynamic table can
have.  The smallest entry has empty name and value strings and has the size of
32.  Hence `MaxEntries` is calculated as

~~~
   MaxEntries = floor( MaxTableCapacity / 32 )
~~~

`MaxTableCapacity` is the maximum capacity of the dynamic table as specified by
the decoder (see {{maximum-dynamic-table-capacity}}).

This encoding limits the length of the prefix on long-lived connections.

The decoder can reconstruct the Required Insert Count using an algorithm such as
the following.  If the decoder encounters a value of EncodedInsertCount that
could not have been produced by a conformant encoder, it MUST treat this as a
stream error of type `HTTP_QPACK_DECOMPRESSION_FAILED`.

TotalNumberOfInserts is the total number of inserts into the decoder's dynamic
table.

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

For example, if the dynamic table is 100 bytes, then the Required Insert Count
will be encoded modulo 6.  If a decoder has received 10 inserts, then an encoded
value of 3 indicates that the Required Insert Count is 9 for the header block.

#### Base {#base}

The `Base` is used to resolve references in the dynamic table as described in
{{relative-indexing}}.

To save space, the Base is encoded relative to the Insert Count using a one-bit
sign and the `Delta Base` value.  A sign bit of 0 indicates that the Base is
greater than or equal to the value of the Insert Count; the value of Delta Base
is added to the Insert Count to determine the value of the Base.  A sign bit of
1 indicates that the Base is less than the Insert Count.  That is:

~~~
   if S == 0:
      Base = ReqInsertCount + DeltaBase
   else:
      Base = ReqInsertCount - DeltaBase - 1
~~~

A single-pass encoder determines the Base before encoding a header block.  If
the encoder inserted entries in the dynamic table while encoding the header
block, Required Insert Count will be greater than the Base, so the encoded
difference is negative and the sign bit is set to 1.  If the header block did
not reference the most recent entry in the table and did not insert any new
entries, the Base will be greater than the Required Insert Count, so the delta
will be positive and the sign bit is set to 0.

An encoder that produces table updates before encoding a header block might set
Required Insert Count and the Base to the same value.  In such case, both the
sign bit and the Delta Base will be set to zero.

A header block that does not reference the dynamic table can use any value for
the Base; setting Delta Base to zero is the most efficient encoding.

For example, with an Required Insert Count of 9, a decoder receives a S bit of 1
and a Delta Base of 2.  This sets the Base to 6 and enables post-base indexing
for three entries.  In this example, a regular index of 1 refers to the 5th
entry that was added to the table; a post-base index of 1 refers to the 8th
entry.


### Indexed Header Field

An indexed header field representation identifies an entry in either the static
table or the dynamic table and causes that header field to be added to the
decoded header list, as described in Section 3.2 of [RFC7541].

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 1 | S |      Index (6+)       |
+---+---+-----------------------+
~~~~~~~~~~
{: title="Indexed Header Field"}

If the entry is in the static table, or in the dynamic table with an absolute
index less than the Base, this representation starts with the '1' 1-bit pattern,
followed by the `S` bit indicating whether the reference is into the static
(S=1) or dynamic (S=0) table. Finally, the relative index of the matching header
field is represented as an integer with a 6-bit prefix (see Section 5.1 of
[RFC7541]).


### Indexed Header Field With Post-Base Index

If the entry is in the dynamic table with an absolute index greater than or
equal to the Base, the representation starts with the '0001' 4-bit pattern,
followed by the post-base index (see {{post-base}}) of the matching header
field, represented as an integer with a 4-bit prefix (see Section 5.1 of
[RFC7541]).

~~~~~~~~~~ drawing
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 0 | 0 | 0 | 1 |  Index (4+)   |
+---+---+---+---+---------------+
~~~~~~~~~~
{: title="Indexed Header Field with Post-Base Index"}


### 具有名称引用的文本标头字段(Literal Header Field With Name Reference)

具有名称引用的文本标头字段表示标头字段名称与存储在静态表或动态表中的条目的标头字段名称
相匹配的标头。

如果条目位于静态表或动态表中，且绝对索引小于Base，则此表示以‘01’两位模式开始。如果该条
目位于动态表中，且绝对索引大于或等于Base，则表示将以“0000”四位模式开始。

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

对于静态表或动态表中绝对索引小于Base的条目，标头字段名称使用该条目的相对索引表示，该索
引表示为具有4位前缀的整数(参见[RFC7541]的5.1节)。S位指示引用是静态(S=1)还是动态(S=0)表。

### 具有后基名称引用的文本标头字段(Literal Header Field With Post-Base Name Reference)


对于动态表中绝对索引大于或等于Base的条目，标头字段名称使用该条目的后基索引
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
{: title="具有后基名称引用的文本标头字段"}


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
