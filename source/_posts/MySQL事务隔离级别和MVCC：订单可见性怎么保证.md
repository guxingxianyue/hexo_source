---
title: MySQL事务隔离级别和MVCC：订单可见性怎么保证
date: 2025-04-17 09:50:00
tags: [MySQL, MVCC, 事务隔离级别, InnoDB, 订单系统]
---

事务隔离级别决定了一个事务能看到哪些数据。MVCC 则是 InnoDB 在不阻塞普通读的情况下实现一致性读的重要机制。供应链系统里，订单、库存、采购、结算这些流程都依赖事务隔离：用户不能看到半提交的数据，后台任务不能基于不一致快照生成错误计划。

理解 MVCC 的关键是区分快照读和当前读。普通 `SELECT` 多数情况下是快照读，`SELECT FOR UPDATE`、`UPDATE`、`DELETE` 是当前读。很多锁问题来自把这两类读混在一起理解。

## 隔离级别解决什么问题

常见并发异常包括：

- 脏读：读到其他事务尚未提交的数据。
- 不可重复读：同一事务内两次读取同一行，结果不同。
- 幻读：同一事务内两次范围查询，出现新增或消失的记录。

供应链例子：计划系统正在生成某仓库的补货建议，它先读取库存，再读取未完成订单。如果读取过程中其他事务提交了大量订单，计划结果就可能基于前后不一致的数据。

MySQL InnoDB 常用隔离级别是 `READ COMMITTED` 和 `REPEATABLE READ`。很多项目默认使用 `REPEATABLE READ`。

## MVCC 的核心概念

MVCC 可以理解为多版本并发控制。每行数据背后有事务版本信息，历史版本保存在 undo log 里。事务执行快照读时，会根据 ReadView 判断哪个版本对当前事务可见。

普通查询：

```sql
SELECT available_qty
FROM scm_inventory
WHERE warehouse_id = 8 AND sku_id = 1001;
```

通常不会加行锁，而是读取一个对当前事务可见的版本。这就是为什么大量查询不会互相阻塞更新。

当前读：

```sql
SELECT available_qty
FROM scm_inventory
WHERE warehouse_id = 8 AND sku_id = 1001
FOR UPDATE;
```

它读取最新已提交版本，并尝试加排他锁。当前读要参与并发修改，所以必须面对锁等待。

## READ COMMITTED 和 REPEATABLE READ 的差异

在 `READ COMMITTED` 下，每条语句都会生成新的 ReadView。一个事务内两次普通查询，可能看到其他事务刚提交的新结果。

在 `REPEATABLE READ` 下，事务第一次快照读时生成 ReadView，后续普通查询沿用这个 ReadView。因此同一事务内多次查询结果更稳定。

供应链报表生成适合使用快照一致性。比如生成某一天的库存余额报表，如果事务内多次查询库存和流水，希望读到同一个时间点的视图。

但订单审核、库存扣减不能只依赖快照读。它们要修改最新状态，应该使用当前读或条件更新。

## Demo：订单审核不能只用快照读

错误示例：

```java
@Transactional
public void approveOrder(long orderId) {
    Order order = orderMapper.selectById(orderId); // 普通快照读
    if (!"WAIT_APPROVE".equals(order.getStatus())) {
        throw new BizException("状态不允许审核");
    }
    orderMapper.updateStatus(orderId, "APPROVED");
}
```

如果两个审核线程同时进入，都可能读到 `WAIT_APPROVE`。虽然最终数据库更新有锁，但如果 `updateStatus` 没有带状态条件，就可能出现重复审核日志、重复发消息。

改进方式：

```java
@Transactional
public void approveOrder(long orderId, long userId) {
    int affected = orderMapper.approve(orderId, userId);
    if (affected != 1) {
        throw new BizException("订单状态已变化，不能重复审核");
    }
    auditLogMapper.insert(orderId, userId, "APPROVE");
}
```

SQL：

```sql
UPDATE scm_sales_order
SET status = 'APPROVED',
    approved_by = #{userId},
    approved_at = NOW()
WHERE id = #{orderId}
  AND status = 'WAIT_APPROVE';
```

这里用当前读的更新语义和状态条件一起保证并发安全。即使两个事务同时执行，也只有一个事务能更新成功。

## MVCC 和锁的关系

MVCC 让普通读不阻塞写，写也不阻塞普通读。但它不意味着没有锁。更新、删除、当前读仍然需要加锁。

库存扣减：

```sql
UPDATE scm_inventory
SET available_qty = available_qty - 3
WHERE warehouse_id = 8
  AND sku_id = 1001
  AND available_qty >= 3;
```

这不是快照读。InnoDB 要读取最新可更新版本并加排他锁。如果另一个事务正在修改同一库存记录，当前事务会等待。

## 供应链系统的使用建议

报表、看板、查询列表主要依赖快照读。它们要求读性能和一致视图，不应该随便加 `FOR UPDATE`。

审核、扣减、占用、释放、结算过账属于状态变更，要用条件更新或当前读。业务状态必须放在 SQL 条件里。

跨多张表的一致性流程要控制事务边界。比如创建出库单并扣库存，应该在一个事务里完成核心数据修改，但不要把 WMS 远程通知放进事务。

对于长报表，不要长时间开启事务读取大量数据，否则会影响 undo log 清理。可以用离线快照表、分批读取或数据仓库承接。

## 小结

MVCC 解决的是读写并发下的一致性读，不是所有并发修改的万能保护。供应链系统要区分快照读和当前读：查询列表依赖 MVCC，状态变更依赖锁和条件更新。把业务状态写进 SQL 条件，是比单纯依赖 Java 判断更可靠的并发控制方式。

