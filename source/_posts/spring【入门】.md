---
title: Spring入门：IoC、DI和供应链服务分层
date: 2016-04-02 19:21:08
tags: [Java, Spring, IoC, DI, 供应链系统]
---

Spring 的核心价值是把对象创建、依赖管理和横切能力交给容器处理，让业务代码专注于业务规则。对于供应链系统来说，订单、库存、仓储、采购、物流、财务等模块依赖关系复杂，如果所有对象都由代码手动创建，系统会很快变得难以维护。

## 整体流程

![Spring IoC 与服务分层流程](/images/tech-flowcharts/spring-ioc-layer-flow.svg)

## IoC 和 DI

IoC 是控制反转。对象不再自己创建依赖，而是由 Spring 容器创建并注入。

DI 是依赖注入。一个类需要什么依赖，就通过构造器、字段或 setter 交给 Spring 注入。推荐使用构造器注入，因为依赖关系更明确，也更利于测试。

```java
@Service
public class OrderCreateService {
    private final InventoryService inventoryService;
    private final OrderRepository orderRepository;

    public OrderCreateService(InventoryService inventoryService,
                              OrderRepository orderRepository) {
        this.inventoryService = inventoryService;
        this.orderRepository = orderRepository;
    }

    public void createOrder(CreateOrderCommand command) {
        inventoryService.reserve(command.skuId(), command.quantity());
        orderRepository.save(command);
    }
}
```

`OrderCreateService` 不关心 `InventoryService` 和 `OrderRepository` 如何创建，Spring 会在启动时完成依赖装配。

## Bean 生命周期

Spring 管理的对象称为 Bean。一个 Bean 大致经历：

1. 扫描或配置定义。
2. 实例化对象。
3. 注入依赖。
4. 初始化。
5. 进入可用状态。
6. 容器关闭时销毁。

示例：

```java
@Component
public class WarehouseRouteCache {
    private Map<String, String> routeMap;

    @PostConstruct
    public void init() {
        routeMap = loadRouteRules();
    }
}
```

缓存预热可以放在初始化阶段，但要注意失败处理。生产系统不建议在静态代码块里做数据库查询或远程调用。

## 供应链服务分层

一个典型订单服务可以分为：

```text
Controller  -> 接收 HTTP 请求
Service     -> 编排业务流程和事务
Repository  -> 数据访问
Client      -> 调用外部系统
Domain      -> 承载核心业务规则
```

示例：

```java
@RestController
@RequestMapping("/orders")
public class OrderController {
    private final OrderCreateService orderCreateService;

    public OrderController(OrderCreateService orderCreateService) {
        this.orderCreateService = orderCreateService;
    }

    @PostMapping
    public void create(@RequestBody CreateOrderCommand command) {
        orderCreateService.createOrder(command);
    }
}
```

分层的关键是职责清晰。Controller 不写复杂业务，Repository 不写业务判断，Service 不做大量 SQL 拼接。

## AOP 的作用

Spring AOP 适合处理横切关注点，例如事务、日志、监控、权限校验。

最典型的是事务：

```java
@Transactional(rollbackFor = Exception.class)
public void reserveStock(ReserveStockCommand command) {
    inventoryRepository.reserve(command.skuId(), command.quantity());
    inventoryLogRepository.insertReserveLog(command);
}
```

这里的事务不是业务方法手动提交，而是通过 Spring 代理在方法前后开启、提交或回滚。

## 常见误区

第一，把所有类都加 `@Service`。注解不是越多越好，只有需要容器管理的对象才应该成为 Bean。

第二，循环依赖。订单服务依赖库存服务，库存服务又依赖订单服务，通常说明边界设计不清晰，需要抽出领域服务或事件机制。

第三，在事务里做远程调用。远程调用会拉长数据库锁持有时间，容易造成锁等待。

第四，忽略测试。构造器注入可以让单元测试直接传入 mock 对象，不必启动完整 Spring 容器。

## 小结

Spring 入门重点不是背 XML 配置，而是理解容器、依赖注入、Bean 生命周期、AOP 和分层边界。供应链系统模块多、链路长，Spring 的价值是把通用工程能力交给框架，把业务复杂度留在清晰的 Service 和领域模型里。
