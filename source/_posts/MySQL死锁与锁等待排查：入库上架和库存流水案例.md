---
title: MySQL死锁与锁等待排查：入库上架和库存流水案例
date: 2025-05-15 09:40:00
tags: [MySQL, 死锁, 锁等待, InnoDB, 仓储系统]
---

死锁不是 MySQL 的异常行为，而是并发系统的正常风险。只要多个事务以不同顺序持有资源并等待对方，就可能死锁。InnoDB 会自动检测死锁，并回滚其中一个事务。业务系统需要做的是降低死锁概率，并在发生死锁时能快速定位和恢复。

供应链系统里，入库上架、库存转移、订单扣减都容易出现死锁，因为这些流程通常会同时更新库存主表、库存流水表、批次表和单据状态。

## 入库上架死锁案例

入库上架时，系统要把待上架数量转成可用库存：

```sql
UPDATE scm_inventory
SET available_qty = available_qty + 10
WHERE warehouse_id = 8 AND sku_id = 1001;

INSERT INTO scm_inventory_log(...)
VALUES (...);

UPDATE scm_receipt_detail
SET putaway_qty = putaway_qty + 10
WHERE receipt_id = 5001 AND sku_id = 1001;
```

另一个任务可能先更新入库明细，再更新库存：

```sql
UPDATE scm_receipt_detail
SET checked_qty = checked_qty + 10
WHERE receipt_id = 5001 AND sku_id = 1001;

UPDATE scm_inventory
SET available_qty = available_qty + 10
WHERE warehouse_id = 8 AND sku_id = 1001;
```

事务 A 持有库存记录，等待入库明细。事务 B 持有入库明细，等待库存记录。两边互相等待，就形成死锁。

## 死锁的四个条件

死锁通常满足四个条件：

- 互斥：资源一次只能被一个事务持有。
- 持有并等待：事务持有一个锁，同时等待另一个锁。
- 不可抢占：锁只能由持有者提交或回滚后释放。
- 循环等待：多个事务形成等待环。

业务上最容易控制的是循环等待。只要固定加锁顺序，就能显著降低死锁概率。

## 固定加锁顺序

对库存转移来说，要从 A 库位转到 B 库位。两个事务方向相反时容易死锁：

```text
事务 1：锁 A，再锁 B
事务 2：锁 B，再锁 A
```

解决办法是按稳定规则排序，比如按库存记录 ID 升序加锁：

```java
@Transactional
public void transfer(long fromInventoryId, long toInventoryId, int qty) {
    List<Long> ids = Stream.of(fromInventoryId, toInventoryId)
        .sorted()
        .toList();

    inventoryMapper.selectForUpdate(ids.get(0));
    inventoryMapper.selectForUpdate(ids.get(1));

    inventoryMapper.decrease(fromInventoryId, qty);
    inventoryMapper.increase(toInventoryId, qty);
    inventoryLogMapper.insertTransferLog(fromInventoryId, toInventoryId, qty);
}
```

SQL：

```sql
SELECT id
FROM scm_inventory
WHERE id = #{id}
FOR UPDATE;
```

即使业务方向不同，底层锁顺序一致，死锁概率会低很多。

## 缩短事务范围

错误做法：

```java
@Transactional
public void putaway(PutawayCommand command) {
    inventoryMapper.lockInventory(command.skuId());
    supplierClient.checkQuality(command.supplierId());
    wmsClient.notifyPutaway(command.taskId());
    inventoryMapper.increase(command.skuId(), command.qty());
}
```

这段代码在事务里做远程调用。远程调用期间数据库锁一直不释放，任何并发库存操作都可能等待。

改进方式是把远程调用放在事务外，事务里只做核心数据变更：

```java
public void putaway(PutawayCommand command) {
    supplierClient.checkQuality(command.supplierId());
    doPutawayInTransaction(command);
    eventPublisher.publishPutawayFinished(command.taskId());
}

@Transactional
public void doPutawayInTransaction(PutawayCommand command) {
    inventoryMapper.increase(command.skuId(), command.qty());
    receiptMapper.markPutaway(command.receiptDetailId(), command.qty());
    inventoryLogMapper.insertPutawayLog(command);
}
```

## 如何排查锁等待

第一步看当前连接：

```sql
SHOW PROCESSLIST;
```

第二步看 InnoDB 状态：

```sql
SHOW ENGINE INNODB STATUS;
```

重点找：

- `LATEST DETECTED DEADLOCK`
- 等待的锁类型。
- 等待的索引。
- 涉及的 SQL。
- 哪个事务被回滚。

MySQL 8 可以查询：

```sql
SELECT *
FROM performance_schema.data_locks;

SELECT *
FROM performance_schema.data_lock_waits;
```

结合事务表可以定位阻塞链：

```sql
SELECT r.trx_id waiting_trx,
       r.trx_mysql_thread_id waiting_thread,
       b.trx_id blocking_trx,
       b.trx_mysql_thread_id blocking_thread
FROM information_schema.innodb_lock_waits w
JOIN information_schema.innodb_trx b
  ON b.trx_id = w.blocking_trx_id
JOIN information_schema.innodb_trx r
  ON r.trx_id = w.requesting_trx_id;
```

不同版本系统表略有差异，核心思路是找到等待者、阻塞者和对应 SQL。

## 业务层重试

死锁发生时，InnoDB 会回滚一个事务。对于库存扣减、上架、状态流转这类短事务，可以做有限重试：

```java
public void putawayWithRetry(PutawayCommand command) {
    for (int i = 0; i < 3; i++) {
        try {
            putawayService.doPutawayInTransaction(command);
            return;
        } catch (DeadlockLoserDataAccessException e) {
            sleep(50L * (i + 1));
        }
    }
    throw new BizException("上架繁忙，请稍后重试");
}
```

重试必须满足幂等。比如上架流水要有业务唯一键，避免第一次事务部分成功但应用误判后重复写入。通常建议给业务流水加唯一键：

```sql
UNIQUE KEY uk_biz_event (biz_type, biz_id)
```

## 小结

死锁排查不能只看异常栈，要回到事务里的 SQL 顺序、索引和持锁时间。供应链系统降低死锁的关键措施是：固定加锁顺序，缩短事务范围，避免事务内远程调用，保证 SQL 命中索引，对可重试短事务做有限幂等重试。

