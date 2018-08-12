title: kafka集群
date: 2017-01-07 12:16:17
tags: [分布式]
---

## Kafka初识

* Kafka使用背景

	在我们大量使用分布式数据库、分布式计算集群的时候，是否会遇到这样的一些问题：
	* 我们想分析下用户行为（pageviews），以便我们设计出更好的广告位
	* 我想对用户的搜索关键词进行统计，分析出当前的流行趋势
	* 有些数据，存储数据库浪费，直接存储硬盘效率又低
	
* Kafka的定义

	它是一个分布式消息系统,具有高水平扩展和高吞吐量的特点。
	

## Kafka相关概念

* AMQP协议：是一个标准开放的应用层的消息中间件（Message Oriented Middleware）协议。AMQP定义了通过网络发送的字节流的数据格式。因此兼容性非常好，任何实现AMQP协议的程序都可以和与AMQP协议兼容的其他程序交互，可以很容易做到跨语言，跨平台。

* 一些基本的概念
  * 消费者：（Consumer）：从消息队列中请求消息的客户端应用程序
  * 生产者：（Producer）：向broker发布消息的应用程序
  * AMQP服务端（broker）：用来接收生产者发送的消息并将这些消息路由给服务器中的队列，便于fafka将生产者发送的消息，动态的添加到磁盘并给每一条消息一个偏移量，所以对于kafka一个broker就是一个应用程序的实例

kafka支持的客户端语言：Kafka客户端支持当前大部分主流语言，包括：C、C++、Erlang、Java、.net、perl、PHP、Python、Ruby、Go、Javascript
可以使用以上任何一种语言和kafka服务器进行通信（即辨析自己的consumer从kafka集群订阅消息也可以自己写producer程序）

* Kafka架构

	生产者生产消息、kafka集群、消费者获取消息这样一种架构，如下图：
	
	![](https://i.imgur.com/fFh8aZr.png)

	kafka集群中的消息，是通过Topic（主题）来进行组织的，如下图：
	
	![](https://i.imgur.com/yMOoyNJ.png)

	一些基本的概念：
	* 主题（Topic）：一个主题类似新闻中的体育、娱乐、教育等分类概念，在实际工程中通常一个业务一个主题。
	* 分区（Partition）：一个Topic中的消息数据按照多个分区组织，分区是kafka消息队列组织的最小单位，一个分区可以看作是一个FIFO（ First Input First Output的缩写，先入先出队列）的队列。
	
	kafka分区是提高kafka性能的关键所在，当你发现你的集群性能不高时，常用手段就是增加Topic的分区，分区里面的消息是按照从新到老的顺序进行组织，消费者从队列头订阅消息，生产者从队列尾添加消息。

	工作图：
	![](https://i.imgur.com/4eSzo4r.png)

	备份（Replication）：为了保证分布式可靠性，kafka0.8开始对每个分区的数据进行备份（不同的Broker上），防止其中一个Broker宕机造成分区上的数据不可用。
	
## Kafka集群搭建
* 软件环境
  * 已经搭建好的zookeeper集群(文章最后另写)
  * 软件版本kafka_2.11-0.9.0.1.tgz
  * 软件版本kafka_2.11-0.9.0.1.tgz
  
* 创建目录并下载安装软件
		#下载软件
		wget https://archive.apache.org/dist/kafka/0.9.0.1/kafka_2.11-0.9.0.1.tgz
		#解压软件
		tar -xvf kafka_2.11-0.9.0.1.tgz
* 修改配置文件

	主要关注config/server.properties 	
	
		broker.id=0  #当前机器在集群中的唯一标识，和zookeeper的myid性质一样
		port=9092 #当前kafka对外提供服务的端口默认是9092
		host.name = 120.76.230.134 #这个参数默认是关闭的，在0.8.1有个bug，DNS解析问题，失败率的问题
		#申明此kafka服务器需要监听的端口号，如果是在本机上跑虚拟机运行可以不用配置本项，默认会使用localhost的地址，如果是在远程服务器上运行则必须配置
		listeners = PLAINTEXT://120.76.230.134:9092 
		advertised.host.name = 120.76.230.134
		advertised.listeners=PLAINTEXT://120.76.230.134:9092
		log.dirs=/data/kafka/kafkalogs  #消息存放的目录
		#在log.retention.hours=168 下面新增下面三项
		message.max.byte=5242880
		default.replication.factor=2
		replica.fetch.max.bytes=5242880
		zookeeper.connect=120.76.230.134:5181,120.76.193.192:5181,120.25.239.155:5181 #zookeeper配置地址

	
	每个机子的broker.id、host.name都是不一样的，主要是关注以上几项参数配置。

* 启动Kafka集群并测试
	
	启动服务
	
		#从后台启动Kafka集群（3台都需要启动）
		cd /data/kafka/kafka_2.11-0.11.0.1/bin #进入到kafka的bin目录 
		./kafka-server-start.sh -daemon ../config/server.properties

	检查服务是否启动

		#执行命令jps
		22246 Bootstrap
		26393 Kafka

	创建Topic来验证是否创建成功

		#创建Topic
		./kafka-topics.sh --create --zookeeper 120.76.230.134:5181,120.76.193.192:5181,120.25.239.155:5181 --replication-factor 2 --partitions 1 --topic test
		
		#解释
		--replication-factor 2   #复制两份
		--partitions 1 #创建1个分区
		--topic #主题为test
		
		#在一台服务器上创建一个发布者
		#创建一个broker，发布者
		./kafka-console-producer.sh --broker-list 120.76.230.134:9092 --topic test
		
		#在一台服务器上创建一个订阅者
		./kafka-console-consumer.sh --bootstrap-server 120.76.230.134:9092 --topic test --from-beginning

	测试（在发布者那里发布消息看看订阅者那里是否能正常收到~）：
	
* 其他命令	

	大部分命令可以去官方文档查看
	* 查看topic
	
			./kafka-topics.sh --list --zookeeper 120.76.230.134:5181,120.76.193.192:5181,120.25.239.155:5181
			#就会显示我们创建的所有topic
	
	kafka集群搭建完毕

## zookeeper集群部署

* 为什么是基数
	
	* 集群必须有一半以上的机器统一才能成为leader
	* 一半的机器挂掉 整个集群挂掉

* 去官网下载好zookeeper包，解压
* 修改配置/conf/zoo.cfg文件

		# 基本事件单元，以毫秒为单位，用来控制心跳和超时
		tickTime=2000
		# 参数设定了允许所有跟随者与领导者进行连接并同步的时间，如果在设定的时间段内，半数以上的跟随者未能完成同步，领导者便会宣布放弃领导地位，进行另一次的领导选举
		# 如果zk集群环境数量确实很大，同步数据的时间会变长，因此这种情况下可以适当调大该参数
		#集群中的follower服务器(F)与leader服务器(L)之间 初始连接 时能容忍的最多心跳数（tickTime的数量）
		initLimit=10
		# 参数设定了允许一个跟随者与一个领导者进行同步的时间，如果在设定的时间段内，跟随者未完成同步，它将会被集群丢弃
		# 所有关联到这个跟随者的客户端将连接到另外一个跟随着
		syncLimit=5
		# 存储持久数据的本地文件系统位置
		dataDir=/data/zookeeper-3.4.9/data
		dataLogDir=/data/zookeeper-3.4.9/logs
		# 监听客户端连接的端口
		clientPort=5181
		
		server.1=120.76.230.134:2888:3888
		server.2=120.76.193.192:2888:3888
		server.3=120.25.239.155:2888:3888

		#server.1 这个1是服务器的标识也可以是其他的数字， 表示这个是第几号服务器，用来标识服务器，这个标识要写到快照目录下面myid文件里
		#120.76.230.134为集群里的IP地址，第一个端口是master和slave之间的通信端口，默认是2888，第二个端口是leader选举的端口，集群刚启动的时候选举或者leader挂掉之后进行新的选举的端口默认是3888

	zoo_sample.cfg  这个文件是官方给我们的zookeeper的样板文件，给他复制一份命名为zoo.cfg，zoo.cfg是官方指定的文件命名规则。

* 创建myid文件

	/data/zookeeper-3.4.9/data目录下要配置myid文件，内容跟server.id相对应，比如:1
	
	./zkServer.sh star启动zookeeper，每台都要启动一遍

* 重要配置说明

	* myid文件和server.myid  在快照目录下存放的标识本台服务器的文件，他是整个zk集群用来发现彼此的一个重要标识。

	* zoo.cfg 文件是zookeeper配置文件 在conf目录里。
