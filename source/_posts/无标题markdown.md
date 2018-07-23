title: spring入门
date: 2016-04-02 19:21:08
tags: [技术文章]
---
## spring介绍：

Spring是一个开源框架，它由Rod Johnson创建。它是为了解决企业应用开发的复杂性而创建的。

   Spring使用基本的JavaBean来完成以前只可能由EJB完成的事情。
  然而，Spring的用途不仅限于服务器端的开发。从简单性、可测试性和松耦合的角度而言，任何Java应用都可以从Spring中受益。
  
* 目的：简化Java的开发
  * 基于POJO轻量级和最小侵入式开发
  * 通过依赖注入和面向接口实现松耦合
  * 基于切面和惯例进行声明式编程
  * 通过切面和模板**减少样板式代码 **
* 功能：使用基本的JavaBean代替EJB，并提供了更多的企业应用功能
* 范围：任何Java应用

   
它是一个容器框架，用来装javabean（java对象），中间层框架（万能胶）可以起一个连接作用，比如说把springMVC和Mybatis粘合在一起运用。简单来说，Spring是一个轻量级的控制反转(IoC)和面向切面(AOP)的容器框架。

#### 侵入式概念
Spring是一种非侵入式的框架…

侵入式

* 对于EJB、Struts2等一些传统的框架，通常是要实现特定的接口，继承特定的类才能增强功能

  * 改变了java类的结构

 非侵入式

  * 对于Hibernate、Spring等框架，对现有的类结构没有影响，就能够增强JavaBean的功能
  * 
  
#### 松耦合

一般我们在写程序的时候，都是面向接口编程，通过DaoFactroy等方法来实现松耦合

    private CategoryDao categoryDao = DaoFactory.getInstance().createDao("zhongfucheng.dao.impl.CategoryDAOImpl", CategoryDao.class);

    private BookDao bookDao = DaoFactory.getInstance().createDao("zhongfucheng.dao.impl.BookDaoImpl", BookDao.class);

    private UserDao userDao = DaoFactory.getInstance().createDao("zhongfucheng.dao.impl.UserDaoImpl", UserDao.class);

    private OrderDao orderDao = DaoFactory.getInstance().createDao("zhongfucheng.dao.impl.OrderDaoImpl", OrderDao.class);
    
DAO层和Service层通过DaoFactory来实现松耦合

* 如果Serivce层直接new DaoBook()，那么DAO和Service就紧耦合了【Service层依赖紧紧依赖于Dao】

而Spring给我们更加合适的方法来实现松耦合，并且更加灵活、功能更加强大！->IOC控制反转 

#### 切面编程

切面编程也就是AOP编程，其实我们在也接触过，动态代理就是一种切面编程了。

AOP编程可以简单理解成：在执行某些代码前，执行另外的代码

* Struts2的拦截器也是面向切面编程【在执行Action业务方法之前执行拦截器】

Spring也为我们提供更好地方式来实现面向切面编程！

## 引出Spring

我们试着回顾一下没学Spring的时候，是怎么开发Web项目的

* 实体类--->class User{ }

* dao-->  UserDao{  .. 访问db}

* service--->  UserService{  UserDao userDao = new UserDao();}

* controller---> UserControler{UserService userService = new UserService();}

用户访问：

* Tomcat->action->service->dao

我们来思考几个问题：

* 1、对象创建创建能否写死？

* 2、对象创建细节

  * controller    访问时候创建

  * service   启动时候创建

  * dao       启动时候创建

  * controller  多个 

  * service 一个   

  * dao     一个   

  * 对象数量

  * 创建时间

* 3、对象的依赖关系

  * controller 依赖 service

  * service依赖 dao
  
对于第一个问题和第三个问题，我们可以通过DaoFactory解决掉

对于第二个问题，我们要控制对象的数量和创建事件就有点麻烦了

而Spring框架通过IOC就很好地可以解决上面的问题

#### IOC控制反转

**Spring的核心思想之一：Inversion of Control , 控制反转 IOC**

那么控制反转是什么意思呢？？？对象的创建交给外部容器完成，这个就做控制反转。

* Spring使用控制反转来实现对象不用在程序中写死

* 控制反转解决对象处理问题【把对象交给别人创建】

那么对象的对象之间的依赖关系Spring是怎么做的呢？？**依赖注入，dependency injection.**

* Spring使用依赖注入来实现对象之间的依赖关系

* 在创建完对象之后，对象的关系处理就是依赖注入
* 
上面已经说了，控制反转是通过外部容器完成的，而Spring又为我们提供了这么一个容器，我们一般将这个容器叫做：**IOC容器.**

无论是创建对象、处理对象之间的依赖关系、对象创建的时间还是对象的数量，我们都是在Spring为我们提供的IOC容器上配置对象的信息就好了。

那么使用IOC控制反转这一思想有什么作用呢？

摘取一下来自知乎的部分解释：

> ioc的思想最核心的地方在于，资源不由使用资源的双方管理，而由不使用资源的第三方管理，这可以带来很多好处。第一，资源集中管理，实现资源的可配置和易管理。第二，降低了使用资源双方的依赖程度，也就是我们说的耦合度。也就是说  ，甲方要达成某种目的不需要直接依赖乙方，它只需要达到的目的告诉第三方机构就可以了，比如甲方需要一双袜子，而乙方它卖一双袜子，它要把袜子卖出去，并不需要自己去直接找到一个卖家来完成袜子的卖出。它也只需要找第三方，告诉别人我要卖一双袜子。这下好了，甲乙双方进行交易活动，都不需要自己直接去找卖家，相当于程序内部开放接口，卖家由第三方作为参数传入。甲乙互相不依赖，而且只有在进行交易活动的时候，甲才和乙产生联系。反之亦然。这样做什么好处么呢，甲乙可以在对方不真实存在的情况下独立存在，而且保证不交易时候无联系，想交易的时候可以很容易的产生联系。甲乙交易活动不需要双方见面，避免了双方的互不信任造成交易失败的问题。因为交易由第三方来负责联系，而且甲乙都认为第三方可靠。那么交易就能很可靠很灵活的产生和进行了。这就是ioc的核心思想。生活中这种例子比比皆是，支付宝在整个淘宝体系里就是庞大的ioc容器，交易双方之外的第三方，提供可靠性可依赖可灵活变更交易方的资源管理中心。另外人事代理也是，雇佣机构和个人之外的第三方。
> ==========================update===========================
> 在以上的描述中，诞生了两个专业词汇，依赖注入和控制反转所谓的依赖注入，则是，甲方开放接口，在它需要的时候，能够讲乙方传递进来(注入)所谓的控制反转，甲乙双方不相互依赖，交易活动的进行不依赖于甲乙任何一方，整个活动的进行由第三方负责管理。

* 不用自己组装，拿来就用。

* 享受单例的好处，效率高，不浪费空间。

* 便于单元测试，方便切换mock组件。

* 便于进行AOP操作，对于使用者是透明的。

* 统一配置，便于修改。

#### Spring模块 

Spring可以分为6大模块：

* Spring Core  spring的核心功能： IOC容器, 解决对象创建及依赖关系

* Spring Web  Spring对web模块的支持。

  * 可以与struts整合,让struts的action创建交给spring

  * spring mvc模块

* Spring DAO  Spring 对jdbc操作的支持  【JdbcTemplate模板工具类】

* Spring ORM  spring对orm的支持：

  * 既可以与hibernate整合，【session】

  * 也可以使用spring的对hibernate操作的封装

* Spring AOP  切面编程

* SpringEE   spring 对javaEE其他模块的支持

![](https://i.imgur.com/jRfjJiS.jpg) 

上面文主要引出了为啥我们需要使用Spring框架，以及大致了解了Spring是分为六大模块的….下面主要讲解Spring的core模块！

## Core模块快速入门

#### 搭建配置环境

引入jar包:

本博文主要是core模块的内容，涉及到Spring core的开发jar包有五个：
* commons-logging-1.1.3.jar           日志

* spring-beans-3.2.5.RELEASE.jar        bean节点

* spring-context-3.2.5.RELEASE.jar       spring上下文节点

* spring-core-3.2.5.RELEASE.jar         spring核心功能

* spring-expression-3.2.5.RELEASE.jar    spring表达式相关表

主要使用的是Spring3.2版本

编写配置文件:

Spring核心的配置文件applicationContext.xml

那这个配置文件怎么写呢？？一般地，我们都知道框架的配置文件都是有约束的…我们可以在spring-framework-3.2.5.RELEASE\docs\spring-framework-reference\htmlsingle\index.html找到XML配置文件的约束

    <beans xmlns="http://www.springframework.org/schema/beans"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:p="http://www.springframework.org/schema/p"
        xmlns:context="http://www.springframework.org/schema/context"
        xsi:schemaLocation="
            http://www.springframework.org/schema/beans
            http://www.springframework.org/schema/beans/spring-beans.xsd
            http://www.springframework.org/schema/context
            http://www.springframework.org/schema/context/spring-context.xsd">
    
    </beans>  
    
我是使用Intellij Idea集成开发工具的，可以选择自带的Spring配置文件,它长的是这样：

    <?xml version="1.0" encoding="UTF-8"?>
    <beans xmlns="http://www.springframework.org/schema/beans"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xsi:schemaLocation="http://www.springframework.org/schema/beans http://www.springframework.org/schema/beans/spring-beans.xsd">
    
    </beans>
    
前面在介绍Spring模块的时候已经说了，Core模块是：**IOC容器，解决对象创建和之间的依赖关系。**

因此**Core模块主要是学习如何得到IOC容器，通过IOC容器来创建对象、解决对象之间的依赖关系、IOC细节。**

#### 得到Spring容器对象【IOC容器】

Spring容器不单单只有一个，可以归为两种类型

* **Bean工厂，BeanFactory【功能简单**

* **应用上下文，ApplicationContext【功能强大，一般我们使用这个】**

==**通过Resource获取BeanFactory**==
* 加载Spring配置文件
* 通过XmlBeanFactory+配置文件来创建IOC容器

        //加载Spring的资源文件
        Resource resource = new ClassPathResource("applicationContext.xml");
        
        //创建IOC容器对象【IOC容器=工厂类+applicationContext.xml】
        BeanFactory beanFactory = new XmlBeanFactory(resource);
    
==**类路径下XML获取ApplicationContext**==
* 直接通过ClassPathXmlApplicationContext对象来获取

        // 得到IOC容器对象
        ApplicationContext ac = new ClassPathXmlApplicationContext("applicationContext.xml");

        System.out.println(ac);
        
在Spring中总体来看可以通过三种方式来配置对象:

* 使用XML文件配置
* 使用注解来配置

#### XML配置方式

在上面我们已经可以得到IOC容器对象了。接下来就是在applicationContext.xml文件中配置信息【让IOC容器根据applicationContext.xml文件来创建对象】

    * 首先我们先有个JavaBean的类
    
    /**
     * Created by ozc on 2017/5/10.
     */
    public class User {
    
        private String id;
        private String username;
    
    
        public String getId() {
            return id;
        }
    
        public void setId(String id) {
            this.id = id;
        }
    
        public String getUsername() {
            return username;
        }
    
        public void setUsername(String username) {
            this.username = username;
        }
    }
    
以前我们是通过new User的方法创建对象

现在我们有了IOC容器，可以让IOC容器帮我们创建对象了。在applicationContext.xml文件中配置对应的信息就行了

       <!--
    使用bean节点来创建对象
    id属性标识着对象
    name属性代表着要创建对象的类全名
    -->
    <bean id="user" class="User"/>
    
    
**通过IOC容器对象获取对象:**

* 在外界通过IOC容器对象得到User对象

        // 得到IOC容器对象
        ApplicationContext ac = new ClassPathXmlApplicationContext("applicationContext.xml");

        User user = (User) ac.getBean("user");

        System.out.println(user);
        
上面我们使用的是IOC通过无参构造函数来创建对象，我们来回顾一下一般有几种创建对象的方式：
* 无参构造函数创建对象
* 带参数的构造函数创建对象
* 工厂创建对象
  * 静态方法创建对象
  * 非静态方法创建对象
   
使用无参的构造函数创建对象我们已经会了，接下来我们看看使用剩下的IOC容器是怎么创建对象的。

==**带参数的构造函数创建对象**==

首先，JavaBean就要提供带参数的构造函数：

    public User(String id, String username) {
        this.id = id;
        this.username = username;
    }
    
接下来，关键是怎么配置applicationContext.xml文件了。

    <bean id="user" class="User">
        <!--通过constructor这个节点来指定构造函数的参数类型、名称、第几个-->
        <constructor-arg index="0" name="id" type="java.lang.String" value="1"></constructor-arg>
        <constructor-arg index="1" name="username" type="java.lang.String" value="zhongfucheng"></constructor-arg>
    </bean>
    
在constructor上如果构造函数的值是一个对象，而不是一个普通类型的值，我们就需要用到ref属性了，而不是value属性

比如说：我在User对象上维护了Person对象的值，想要在构造函数中初始化它。因此，就需要用到ref属性了

    <bean id="person" class="Person"></bean> 

    <bean id="user" class="User" >

        <!--通过constructor这个节点来指定构造函数的参数类型、名称、第几个-->
        <constructor-arg index="0" name="id" type="java.lang.String" value="1"></constructor-arg>
        <constructor-arg index="1" name="username" type="java.lang.String" ref="person"></constructor-arg>
    </bean>
    
**==工厂静态方法创建对象==**

首先，使用一个工厂的静态方法返回一个对象

    public class Factory {
    
        public static User getBean() {
    
            return new User();
        }
    
    }
    
配置文件中使用工厂的静态方法返回对象

    <!--工厂静态方法创建对象，直接使用class指向静态类，指定静态方法就行了-->
    <bean id="user" class="Factory" factory-method="getBean" >

    </bean>
    
**==工厂非静态方法创建对象==**

首先，也是通过工厂的非静态方法来得到一个对象

    public class Factory {
    
    
        public User getBean() {
    
            return new User();
        }
    
    
    }
    
配置文件中使用工厂的非静态方法返回对象

    <!--首先创建工厂对象-->
    <bean id="factory" class="Factory"/>

    <!--指定工厂对象和工厂方法-->
    <bean id="user" class="User" factory-bean="factory" factory-method="getBean"/>
    
#### 注解方式

通过注解来配置信息就是为了简化IOC容器的配置，注解可以把对象添加到IOC容器中、处理对象依赖关系

使用注解步骤：

* 1）先引入context名称空间
  * xmlns:context="http://www.springframework.org/schema/context"
* 2）开启注解扫描器
  * <context:component-scan base-package=""></context:component-scan>
  
创建对象以及处理对象依赖关系，相关的注解：

* @ComponentScan扫描器
* @Configuration表明该类是配置类
* @Component   指定把一个对象加入IOC容器--->@Name也可以实现相同的效果【一般少用】
* @Repository   作用同@Component； 在持久层使用
* @Service      作用同@Component； 在业务逻辑层使用
* @Controller    作用同@Component； 在控制层使用
* @Resource  依赖关系
  * 如果@Resource不指定值，那么就根据类型来找，相同的类型在IOC容器中不能有两个
  * 如果@Resource指定了值，那么就根据名字来找
  
测试代码:

* UserDao

        package aa;
        
        import org.springframework.stereotype.Repository;
        
        /**
         * Created by ozc on 2017/5/10.
         */
        
        //把对象添加到容器中,首字母会小写
        @Repository
        public class UserDao {
        
            public void save() {
                System.out.println("DB:保存用户");
            }
        
        
        }

* userService

        package aa;
        
        import org.springframework.stereotype.Service;
        
        import javax.annotation.Resource;
        
        
        //把UserService对象添加到IOC容器中,首字母会小写
        @Service
        public class UserService {
        
            //如果@Resource不指定值，那么就根据类型来找--->UserDao....当然了，IOC容器不能有两个UserDao类型的对象
            //@Resource
        
            //如果指定了值，那么Spring就在IOC容器找有没有id为userDao的对象。
            @Resource(name = "userDao")
            private UserDao userDao;
        
            public void save() {
                userDao.save();
            }
        }
        
* userController
* 
        package aa;
        
        import org.springframework.stereotype.Controller;
        
        import javax.annotation.Resource;
        
        /**
         * Created by ozc on 2017/5/10.
         */
        
        //把对象添加到IOC容器中,首字母会小写
        @Controller
        public class UserController {
        
            @Resource(name = "userService")
            private UserService userService;
        
            public String execute() {
                userService.save();
                return null;
            }
        }

* 测试

        package aa;
        
        import org.springframework.context.ApplicationContext;
        import org.springframework.context.support.ClassPathXmlApplicationContext;
        
        /**
         * Created by ozc on 2017/5/10.
         */
        public class App {
        
            public static void main(String[] args) {
        
                // 创建容器对象
                ApplicationContext ac = new ClassPathXmlApplicationContext("aa/applicationContext.xml");
        
                UserAv userController = (UserController) ac.getBean("userController");
        
                userController.execute();
            }
        }

#### bean对象创建细节

在Spring第一篇中，我们为什么要引入Spring提出了这么一些问题：

* 对象创建能否写死？
* 对象创建细节
  * 对象数量
    * controller多个
    * service一个
    * dao一个
  * 创建时间
    * controller访问时创建
    * service启动时创建
    * dao启动时创建

既然我们现在已经初步了解IOC容器了，那么这些问题我们都是可以解决的。并且是十分简单【对象写死问题已经解决了，IOC容器就是控制反转创建对象】

**==scope属性==**

指定scope属性，IOC容器就知道创建对象的时候是单例还是多例的了。

属性的值就只有两个：单例/多例

* 当我们使用singleton【单例】的时候，从IOC容器获取的对象都是同一个
* 当我们使用prototype【多例】的时候，从IOC容器获取的对象都是不同的

scope属性除了控制对象是单例还是多例的，还控制着对象创建的时间！
* 当使用singleton的时候，对象在IOC容器之前就已经创建了
* 当使用prototype的时候，对象在使用的时候才创建

**==lazy==-init属性** 

lazy-init属性只对singleton【单例】的对象有效…..lazy-init默认为false….

有的时候，可能我们想要对象在使用的时候才创建，那么将lazy-init设置为ture就行了

**==init==-method和destroy-method**

如果我们想要对象在创建后，执行某个方法，我们指定为init-method属性就行了。。

如果我们想要IOC容器销毁后，执行某个方法，我们指定destroy-method属性就行了。

     <bean id="user" class="User" scope="singleton" lazy-init="true" init-method="" destroy-method=""/>
     
==**Bean创建细节总结**==

    /**
     * 1) 对象创建： 单例/多例
     *  scope="singleton", 默认值， 即 默认是单例 【service/dao/工具类】
     *  scope="prototype", 多例；              【Action对象】
     * 
     * 2) 什么时候创建?
     *    scope="prototype"  在用到对象的时候，才创建对象。
     *    scope="singleton"  在启动(容器初始化之前)， 就已经创建了bean，且整个应用只有一个。
     * 3)是否延迟创建
     *    lazy-init="false"  默认为false,  不延迟创建，即在启动时候就创建对象
     *    lazy-init="true"   延迟初始化， 在用到对象的时候才创建对象
     *    （只对单例有效）
     * 4) 创建对象之后，初始化/销毁
     *    init-method="init_user"       【对应对象的init_user方法，在对象创建之后执行 】
     *    destroy-method="destroy_user"  【在调用容器对象的destroy方法时候执行，(容器用实现类)】
     */
