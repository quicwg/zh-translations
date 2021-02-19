# QUIC Protocol 相关文档中文翻译

这是 IETF-QUIC-Working-Group 相关文档的翻译所使用的仓库。

翻译将基于最新的 IETF-QUIC-draft 版本, 并跟进将在近期推出的 RFC 完成。

翻译提供当前正在翻译的部分预览，同时提供此前完成的 version 18 的完整翻译内容。

## 完整旧版本在线预览
点击以下链接在线预览V18版本翻译。

[QUIC 传输协议 draft-ietf-quic-transport-zh](http://docs.wxclimb.top/draft-ietf-quic-transport-zh.html)

[QUIC-HTTP 语义映射 draft-ietf-quic-http-zh](http://docs.wxclimb.top/draft-ietf-quic-http-zh.html)

[QUIC-QPACK 封装 draft-ietf-quic-qpack-zh](http://docs.wxclimb.top/draft-ietf-quic-qpack-zh.html)

[QUIC-TLS 加密 draft-ietf-quic-tls-zh](http://docs.wxclimb.top/draft-ietf-quic-tls-zh.html)

[QUIC-Recovery 丢失恢复 draft-ietf-quic-recovery-zh](http://docs.wxclimb.top/draft-ietf-quic-recovery-zh.html)

[QUIC-spin-exp 自旋实践 draft-ietf-quic-spin-exp-zh](http://docs.wxclimb.top/draft-ietf-quic-spin-exp-zh.html)

[QUIC-invariants 不变量 draft-ietf-quic-invariants-zh](http://docs.wxclimb.top/draft-ietf-quic-invariants-zh.html)

## 翻译中最新版本在线预览
点击以下链接在线预览翻译中最新版本翻译。

[QUIC 传输协议 draft-ietf-quic-transport](http://doc.wxclimb.top/draft-ietf-quic-transport.html)

## 翻译格式与翻译相关

* 采用 [IETF Internet Draft 标准格式](https://github.com/martinthomson/i-d-template)
* 一人翻译一人校对，每周发布校对完成的译文到 master 分支

## 本地构建
### Linux依赖安装(Ubuntu为例)
#### xml2rfc
```
curl https://bootstrap.pypa.io/get-pip.py | python
pip install xml2rfc
```
#### mmark(与kramdown-rfc2629二选一)
```
sudo add-apt-repository ppa:gophers/archive
sudo apt-get update
sudo apt-get install golang-1.10-go
go get github.com/miekg/mmark/mmark
go build github.com/miekg/mmark/mmark
```
#### kramdown-rfc2629(与mmark二选一)
```
wget -O ruby-install-0.7.0.tar.gz https://github.com/postmodern/ruby-install/archive/v0.7.0.tar.gz
tar -xzvf ruby-install-0.7.0.tar.gz
cd ruby-install-0.7.0/
sudo make install
ruby-install ruby
gem install kramdown-rfc2629
```
### OSX依赖安装
请参考[这里](https://github.com/martinthomson/i-d-template/blob/master/doc/SETUP.md)
基本上与Linux一致

### 文档构建
将`xml2rfc`, `mmark`, `kramdown-rfc2629`等命令确保在当前环境下可执行(自行修改path)后执行

```
make
make unescape
```

## 欢迎新的贡献者

* 若有翻译错漏问题，请在 issues 中提出
* 若希望参与翻译贡献自己的力量，可发送邮件到([quic@ietf.org][ietf-quic]) 或 ([wuxiao0129@gmail.com][atticuswu])

## 参与人员

由志愿者无私的贡献出自己的业余时间进行翻译，感谢以下人员的贡献（排名不分先后）

* atticuswu ([wuxiao0129@gmail.com][atticuswu])
* holimu ([1398620653@qq.com][holimu])
* steinns ([906060812@qq.com][steinns])
* fuxiuyin ([woshifuxiuyin@gmail.com][fuxiuyin])
* kyjo2014 ([bestkyjo@gmail.com][kyjo2014])
* UNSaWEN([abc7535@vip.qq.com][UNSaWEN])
* zyad86([243019700@qq.com][zyad86])
* lanpishu6300([lanpishu6300@gmail.com][lanpishu6300])

[ietf-quic]: quic@ietf.org
[atticuswu]: wuxiao0129@gmail.com
[holimu]: mailto:1398620653@qq.com
[steinns]: mailto:906060812@qq.com
[fuxiuyin]: mailto:woshifuxiuyin@gmail.com
[kyjo2014]: mailto:bestkyjo@gmail.com
[UNSaWEN]: mailto:abc7535@vip.qq.com
[zyad86]: mailto:243019700@qq.com
[lanpishu6300]: mailto:lanpishu6300@gmail.com
