---
title: Kafka集群：分区、副本和供应链事件流
date: 2017-01-07 21:23:08
tags: [Kafka, 消息队列, 分布式系统, 供应链系统]
---

Kafka 是高吞吐分布式消息系统，适合处理订单事件、库存变更、物流轨迹、仓储作业状态等业务流。学习 Kafka 集群时，不应该只关注配置项，更要理解 Topic、Partition、Replica、Consumer Group 如何共同保证吞吐、扩展性和可用性。

## 整体流程

![Kafka 集群和供应链事件流](/images/tech-flowcharts/kafka-cluster-event-flow.svg)

## Kafka 集群核心概念

Kafka 的基本组件包括：

1. Broker：Kafka 服务节点。
2. Topic：消息主题，例如 `order-created`。
3. Partition：Topic 的分区，用于并行写入和消费。
4. Replica：分区副本，用于容灾。
5. Leader：当前负责读写的分区副本。
6. Follower：跟随 Leader 同步数据。
7. Consumer Group：消费者组，同一组内多个消费者共同消费分区。

分区是 Kafka 扩展吞吐的关键。一个 Topic 有多个分区，生产者可以并行写入，消费者组内的消费者也可以并行消费。

## 供应链事件流例子

订单创建成功后，订单服务可以发送事件：

```json
{
  "eventId": "evt-10001",
  "eventType": "ORDER_CREATED",
  "orderNo": "SO202606280001",
  "warehouseId": 8,
  "occurredAt": "2026-06-28T10:20:00"
}
```

库存服务消费事件后预占库存，仓储服务消费事件后生成出库任务，财务服务消费事件后创建应收记录：

```text
Order Service -> order-created topic
Inventory Service -> reserve stock
WMS Service -> create outbound task
Finance Service -> create receivable
```

这种事件驱动方式能降低服务之间的同步耦合，但也要求下游具备幂等和补偿能力。

## 分区设计

如果同一订单的事件必须按顺序处理，应使用订单号作为 key：

```java
ProducerRecord<String, OrderCreatedEvent> record =
        new ProducerRecord<>("order-created", event.orderNo(), event);
kafkaTemplate.send(record);
```

相同 key 的消息会进入同一分区，从而在该分区内保持顺序。但这不代表整个 Topic 全局有序，Kafka 只保证单分区内有序。

分区数变更也会影响 key 到分区的映射。扩容期间，同一个 key 的新旧消息可能位于不同分区，因此对严格顺序敏感的业务需要设计版本化路由、停写迁移或在消费端按业务版本校验，不能把“使用相同 key”理解成永久顺序保证。

分区数量要结合吞吐和消费者并行度规划。分区太少会限制并发，分区太多会增加元数据、文件句柄和 rebalance 成本。

## 副本和可靠性

生产环境 Topic 应该配置多个副本：

```bash
kafka-topics.sh --create \
  --topic order-created \
  --partitions 12 \
  --replication-factor 3 \
  --bootstrap-server kafka-1:9092
```

生产者可靠性配置：

```properties
acks=all
enable.idempotence=true
retries=2147483647
```

`acks=all` 表示 Leader 等待 ISR 中满足要求的副本确认后才认为写入成功。Broker 端还应设置合适的 `min.insync.replicas`，例如副本数为 3 时设为 2，避免只剩一个同步副本时仍接受关键写入。开启幂等生产者后通常应保留充分的重试机会；具体默认值和兼容约束以当前 Kafka 客户端版本为准。生产者幂等只能约束单个生产者会话内的重试，业务消费者仍然要做幂等。

## 消费幂等

消息系统通常只能帮你降低丢消息和乱序风险，不能自动解决业务重复处理。消费者必须幂等。

```java
@Transactional
public void handle(OrderCreatedEvent event) {
    // event_id 上有唯一索引；插入成功才获得本次处理权。
    if (!eventRepository.tryInsert(event.eventId())) {
        return;
    }

    inventoryService.reserve(event.orderNo(), event.warehouseId());
    eventRepository.markSucceeded(event.eventId());
}
```

“先查询是否存在、再插入”的写法存在并发竞态。更稳妥的方式是依赖数据库唯一约束原子地抢占事件处理权，并把事件记录、库存条件更新和状态变更放在同一事务中。若库存服务和事件表不在同一数据库，则需要 outbox、状态机或补偿任务处理跨系统一致性。

## 常见问题

第一，消费者堆积。要看是消费者处理慢、分区不够、下游数据库慢，还是单条消息失败反复重试。

第二，rebalance 频繁。消费者实例不稳定、处理时间过长或超时配置不合理都可能导致 rebalance。

第三，只关注 Kafka 不关注业务补偿。消息发送成功不代表业务最终成功，库存预占失败、仓储创建失败都需要补偿流程。

第四，把 Kafka 当 RPC。Kafka 适合异步事件，不适合需要立即返回强一致结果的流程。

## 小结

Kafka 集群的关键是分区提升吞吐、副本提升可用性、消费者组提升并行消费能力。供应链系统中，订单、库存、仓储、物流事件非常适合用 Kafka 解耦，但必须配套幂等、补偿、监控和告警，才能真正成为可靠的事件流基础设施。
