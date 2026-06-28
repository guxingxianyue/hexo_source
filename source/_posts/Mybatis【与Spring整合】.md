---
title: MyBatis与Spring整合：事务边界和库存扣减
date: 2016-04-11 20:36:29
tags: [Java, MyBatis, Spring, 事务, 供应链系统]
---

MyBatis 和 Spring 整合后，Mapper 的创建、事务管理、数据源配置都交给 Spring 容器统一管理。业务代码不需要手动创建 `SqlSession`，也不应该在 Service 里手动提交事务。对于供应链系统来说，这一点非常关键，因为库存扣减、订单状态流转、库存流水写入必须处在清晰的事务边界内。

## 整体流程

![MyBatis 与 Spring 事务流程](/images/tech-flowcharts/mybatis-spring-transaction-flow.svg)

## Spring 整合 MyBatis 的核心

整合后通常有三层：

1. Controller：接收请求，做参数校验和返回结果。
2. Service：编排业务流程，定义事务边界。
3. Mapper：执行 SQL，不写业务判断。

Spring Boot 项目里常见依赖是：

```xml
<dependency>
    <groupId>org.mybatis.spring.boot</groupId>
    <artifactId>mybatis-spring-boot-starter</artifactId>
    <version>3.0.3</version>
</dependency>
```

配置示例：

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/scm?useUnicode=true&characterEncoding=utf8
    username: scm_user
    password: your_password
mybatis:
  mapper-locations: classpath*:mapper/**/*.xml
  configuration:
    map-underscore-to-camel-case: true
```

Mapper 扫描：

```java
@SpringBootApplication
@MapperScan("com.example.scm.**.mapper")
public class ScmApplication {
    public static void main(String[] args) {
        SpringApplication.run(ScmApplication.class, args);
    }
}
```

## 供应链例子：库存预占事务

订单创建时，需要把可用库存转成锁定库存，并写入库存流水：

```java
@Service
public class StockReserveService {
    private final InventoryMapper inventoryMapper;
    private final InventoryLogMapper inventoryLogMapper;

    public StockReserveService(InventoryMapper inventoryMapper,
                               InventoryLogMapper inventoryLogMapper) {
        this.inventoryMapper = inventoryMapper;
        this.inventoryLogMapper = inventoryLogMapper;
    }

    @Transactional(rollbackFor = Exception.class)
    public void reserve(ReserveStockCommand command) {
        int affectedRows = inventoryMapper.reserve(
                command.warehouseId(),
                command.skuId(),
                command.quantity()
        );
        if (affectedRows != 1) {
            throw new BizException("库存不足，无法预占");
        }

        inventoryLogMapper.insertReserveLog(command);
    }
}
```

Mapper SQL：

```xml
<update id="reserve">
    UPDATE scm_inventory
    SET available_qty = available_qty - #{quantity},
        locked_qty = locked_qty + #{quantity},
        updated_at = NOW()
    WHERE warehouse_id = #{warehouseId}
      AND sku_id = #{skuId}
      AND available_qty >= #{quantity}
</update>
```

这条 SQL 同时完成判断和扣减，避免先查库存再更新导致并发超卖。`@Transactional` 保证库存表更新和库存流水写入要么同时成功，要么同时回滚。

## 事务边界应该放在哪里

事务应该放在 Service 层，而不是 Controller 或 Mapper 层。

原因是：

1. Controller 负责协议和参数，不应该持有数据库事务。
2. Mapper 只执行单条或少量 SQL，不知道完整业务流程。
3. Service 能表达业务一致性边界，例如“预占库存 + 写流水”必须同事务。

错误写法是把远程调用放在事务中：

```java
@Transactional
public void reserveAndNotify(ReserveStockCommand command) {
    inventoryMapper.reserve(command.warehouseId(), command.skuId(), command.quantity());
    wmsClient.notifyReserve(command.orderNo());
    inventoryLogMapper.insertReserveLog(command);
}
```

远程调用慢或失败时，数据库锁会被长时间持有，容易引发锁等待。更稳妥的方式是事务内只做本地数据变更，事务提交后再发事件：

```java
@Transactional(rollbackFor = Exception.class)
public void reserve(ReserveStockCommand command) {
    int affectedRows = inventoryMapper.reserve(command.warehouseId(), command.skuId(), command.quantity());
    if (affectedRows != 1) {
        throw new BizException("库存不足，无法预占");
    }
    inventoryLogMapper.insertReserveLog(command);
    eventPublisher.publish(new StockReservedEvent(command.orderNo()));
}
```

如果要确保事件和数据库事务一致，可以使用事务消息、outbox 表或 `@TransactionalEventListener`。

## 常见问题

第一，自调用导致事务不生效。Spring 声明式事务通常通过代理实现，同一个类内部方法直接调用可能绕过代理。

第二，异常被吞掉导致事务提交。如果捕获异常后不再抛出，Spring 可能认为方法正常结束。

第三，事务范围太大。事务里不要做 HTTP 调用、文件上传、大量循环查询。

第四，只依赖本地锁保护数据库数据。多实例部署后，本地 `synchronized` 只能锁住当前 JVM，不能保护数据库里的库存。

## 小结

MyBatis 与 Spring 整合的重点不是配置本身，而是把 SQL、Mapper、Service 事务边界组织清楚。供应链系统里最容易出问题的是库存、订单状态和流水一致性，写代码时要明确哪些操作必须同事务，哪些操作应该事务后异步处理。
