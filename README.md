# ROS topic plotter for web edition

该项目基于ROS1，使用rospy和html前端， 配置环境为ubuntu20.04版本。

这个项目实现了将ROS话题信息发送到本地的一个服务器上，通过浏览器访问即可实现ROS话题信息的获取。

支持多个话题的同时获取与曲线查看，曲线更新频率为20hz，足以满足需求。

**对于使用者，只需要使用ssh连接上ROS后端，输入一条指令即可开启该功能，在浏览器输入对应地址即可访问。**



项目前置功能包：rospy_message_converter，需要预先将该功能包放入工作空间构建

github URL：https://github.com/DFKI-NI/rospy_message_converter

具体的部署过程和使用教程详见docs文件夹。