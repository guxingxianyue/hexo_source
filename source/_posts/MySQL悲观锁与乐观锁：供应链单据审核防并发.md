---
title: MySQL悲观锁与乐观锁：供应链单据审核防并发
date: 2025-06-19 09:40:00
tags: [MySQL, 悲观锁, 乐观锁, 单据审核, 供应链系统]
---

悲观锁和乐观锁不是 MySQL 独有的语法，而是两种并发控制思想。悲观锁假设冲突很常见，所以先加锁再修改。乐观锁假设冲突不多，所以先尝试更新，更新时验证版本或状态。

供应链系统里，单据审核、防重复提交、库存预占、结算过账都需要在这两种策略之间做选择。选择标准不是哪个更高级，而是冲突概率、业务代价、事务长度和用户体验。

## 悲观锁和乐观锁选择流程

![MySQL 悲观锁和乐观锁选择流程](/images/tech-flowcharts/mysql-pessimistic-optimistic-flow.svg)

## 悲观锁：先锁住再处理

采购单审核可以使用 `FOR UPDATE`：

```sql
START TRANSACTION;

SELECT id, status, total_amount
FROM scm_purchase_order
WHERE id = 9001
FOR UPDATE;

UPDATE scm_purchase_order
SET status = 'APPROVED',
    approved_by = 101,
    approved_at = NOW()
WHERE id = 9001;

COMMIT;
```

当事务 A 持有这张采购单的排他锁时，事务 B 也执行 `FOR UPDATE` 会等待。这样可以保证同一张单据审核过程串行化。

悲观锁适合冲突概率高、重复执行代价大、必须读取多项数据后才能决定更新的场景。比如结算过账要检查供应商余额、发票状态、入库明细和付款计划，处理过程必须串行。

## 悲观锁的问题

悲观锁的缺点是持锁期间其他事务要等待。如果事务里包含慢操作，影响会放大。

错误示例：

```java
@Transactional
public void approve(long purchaseOrderId) {
    PurchaseOrder order = mapper.selectForUpdate(purchaseOrderId);
    contractClient.check(order.getSupplierId());
    mapper.approve(purchaseOrderId);
}
```

远程合同校验放在事务里，会让数据库锁一直持有。正确做法是事务外做可提前完成的校验，事务内只做最终状态判断和更新。

```java
public void approve(long purchaseOrderId) {
    PurchaseOrderSnapshot snapshot = mapper.selectSnapshot(purchaseOrderId);
    contractClient.check(snapshot.supplierId());
    approveInTransaction(purchaseOrderId);
}

@Transactional
public void approveInTransaction(long purchaseOrderId) {
    PurchaseOrder order = mapper.selectForUpdate(purchaseOrderId);
    if (!order.waitApprove()) {
        throw new BizException("状态已变化");
    }
    mapper.approve(purchaseOrderId);
}
```

## 乐观锁：更新时校验版本

乐观锁通常依赖 `version` 字段：

```sql
ALTER TABLE scm_purchase_order
ADD COLUMN version INT NOT NULL DEFAULT 0;
```

更新时带上旧版本：

```sql
UPDATE scm_purchase_order
SET status = 'APPROVED',
    approved_by = #{userId},
    approved_at = NOW(),
    version = version + 1
WHERE id = #{id}
  AND status = 'WAIT_APPROVE'
  AND version = #{version};
```

如果影响行数是 1，审核成功。如果是 0，说明状态或版本已经被别人改过，业务层提示用户刷新。

Java 代码：

```java
public void approveOptimistic(long id, int version, long userId) {
    int affected = mapper.approve(id, version, userId);
    if (affected != 1) {
        throw new BizException("单据已被其他人处理，请刷新后重试");
    }
}
```

乐观锁适合冲突概率较低、操作短、用户可以接受重试的场景。比如供应商资料维护、采购单草稿编辑、价格策略调整。

## 只用状态条件也可以

很多单据流转不一定需要单独 `version`，状态条件本身就是乐观锁：

```sql
UPDATE scm_sales_order
SET status = 'CANCELLED'
WHERE id = #{id}
  AND status IN ('CREATED', 'WAIT_PAY');
```

如果订单已经出库，更新影响行数为 0。业务层返回“当前状态不允许取消”。

状态条件的优点是表达业务语义，缺点是不能发现所有字段覆盖问题。如果是编辑表单保存，还是应该使用 `version` 或 `updated_at` 防止覆盖别人刚改的内容。

## 库存扣减选哪种

库存扣减常用条件更新：

```sql
UPDATE scm_inventory
SET available_qty = available_qty - #{qty},
    locked_qty = locked_qty + #{qty},
    version = version + 1
WHERE warehouse_id = #{warehouseId}
  AND sku_id = #{skuId}
  AND available_qty >= #{qty};
```

这更像乐观更新，但执行时 InnoDB 仍会对命中的记录加排他锁。它的优势是单 SQL 完成判断和修改，不需要先 `SELECT FOR UPDATE`。

如果扣减逻辑必须读取复杂批次、先进先出规则、多个库位分配，再逐条修改，悲观锁或固定顺序的当前读会更清晰。

## 选择原则

高冲突、强顺序、长业务校验：考虑悲观锁，但事务必须短。

低冲突、短更新、用户可重试：优先乐观锁。

单据状态流转：优先状态条件更新。

库存余额扣减：优先条件更新，必要时结合版本和流水唯一键。

跨系统流程：不要靠长事务持锁等待外部系统，使用状态机、消息表和补偿任务。

## 小结

悲观锁和乐观锁是供应链系统里最常用的并发控制策略。悲观锁强调先占有资源，适合强冲突流程；乐观锁强调提交时校验，适合低冲突编辑和状态流转。实际项目中，两者经常结合使用：数据库条件更新保证最终一致，应用层根据影响行数决定成功、失败或重试。
