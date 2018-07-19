title: Github+hexo 搭建个人独立博客
date: 2015-11-05 23:47:08
tags: [技术文章]
---
## 关于自建独立博客
---
这里引用某位知友的原话：

	自主权比较高，博客平台的话会有这样那样的限制，技术上，可能会限制插件的代码使用，内容上，各种审查以防触雷以及广告等等。

作为一个技术宅，没有比“show me the code”“show me the writings”更有说服力。当然这话是我说的。

## 什么是hexo
---
一个基于Node.js的静态博客程序，可以方便的生成静态网页托管在github上，可以绑定自己的域名，用markdown写文章（简直不要太爽）。

	快速、简单且功能强大的 Node.js 博客框架。
	A fast, simple & powerful blog framework, powered by Node.js.

## 为什么要用hexo
---
* 不可思议的快速，眨眼即可完成
* 支持markdown，支持markdown，支持markdown，重要的话说三遍
* 一道指令即可将文章部署到 GitHub Pages
* 高扩展性、自定义性
* 兼容于 Windows & Mac & Linux
* 易用。不仅部署简单，平时使用中仅需要hexo new、hexo generate、hexo server、hexo deploy四个命令。
* 轻、文件少、小，易理解，方便自定义，

##	谁能使用hexo
---
这是一个免费开源的博客程序，任何人都可以使用和修改，整个独立博客搭建过程仅需要用到Github,Git,Markdown,Node.js这样的工具。好多插件、widget都需要自己安装、设置。比较适合那些有一定计算机基础，喜欢折腾的人。下面我们开始吧!

## 搭建hexo博客（一）
---
**注意：本节教程只针对Windows用户，Linux和Mac用户请移步**

### 安装Git
---
下载[msysgit](http://pan.baidu.com/s/1bcsvP8 "git"),版本最好不要用高于1.8.5，有bug，至少截至2015-12-7年为止，这个bug是有的，此处用的是1.8.4。

### 安装Node.js
---
在 Windows 环境下安装 Node.js很简单，仅须[点此下载](http://pan.baidu.com/s/1dDYO1w9)安装文件并一步一步往下执行即可完成安装。

### 安装hexo
---
利用 npm 命令即可安装。（在任意位置点击鼠标右键，选择Git bash）

		npm install -g hexo

### 创建hexo文件夹
---
安装完成后，在你喜爱的文件夹下（如H:\hexo），执行以下指令(在H:\hexo内点击鼠标右键，选择Git bash)，Hexo 即会自动在目标文件夹建立网站所需要的所有文件。

		hexo init

### 安装依赖包
---

        npm install

### 本地查看
---
现在我们已经搭建起本地的hexo博客了，执行以下命令(在H:\hexo)，然后到浏览器输入```localhost:4000```看看。

		hexo generate
		hexo server

至此，本地博客已经搭建起来了，嘘~~~现在只有你自己能看到，别人是看不到的。下面，我们要部署到Github，让所有人都能看到你的博客。

### 注册Github账号
---
已有账号可以跳过，没有的，[请在此进行注册](https://www.github.com)，很简单，这里就不介绍了。

### 创建repository
---
在自己Github主页右下角，创建一个新的repository。比如我的Github账号是guxingxianyue，那么我应该创建的repository名字应该是guxingxianyue.github.io。

### 部署到Github
---
编辑_config.yml(在H:\hexo下)。你在部署时，要把下面的guxingxianyue都换成你的账号名。

	deploy:
	  type: git
	  repository: https://github.com/guxingxianyue/guxingxianyue.github.io.git
	  branch: master

### 执行下列指令即可完成部署。
---

    npm install hexo-deployer-git --save(有的哥们竟然不需要这个指令也能部署成功)
	hexo generate
	hexo deploy

**注意：**有些新用户需要设置ssh，否则上述命令会失败。ssh 的介绍和设置方法请看[官方教程](https://help.github.com/articles/generating-ssh-keys/)不用担心，很简单。

**记住：**每次修改本地文件后，需要hexo generate才能保存。每次使用命令时，都要在H:\hexo目录下右键选择Git Bash指令窗口。

Okay,至此博客已经完全搭建起来了，在浏览器访问guxingxianyue.github.io就能看到你的成就了！Good luck。


