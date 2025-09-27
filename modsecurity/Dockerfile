# 使用官方Nginx镜像
FROM nginx:latest

# 安装ModSecurity模块
RUN apt-get update && apt-get install -y nginx-extras libmodsecurity3

# 复制Nginx和ModSecurity的配置文件
COPY nginx.conf /etc/nginx/nginx.conf
COPY modsecurity.conf /etc/nginx/modsecurity.conf
COPY owasp-crs.conf /etc/nginx/owasp-crs.conf

# 启用OWASP核心规则集 (一个开源的、强大的攻击特征库)
RUN git clone https://github.com/coreruleset/coreruleset /usr/share/nginx/owasp-crs
RUN mv /usr/share/nginx/owasp-crs/crs-setup.conf.example /usr/share/nginx/owasp-crs/crs-setup.conf