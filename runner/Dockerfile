FROM alpine:3.20
RUN apk add --no-cache openssh-client bash jq
RUN adduser -D -h /home/runner runner

# global ssh config: force publickey only
RUN mkdir -p /etc/ssh && echo '\
Host *\n\
    PreferredAuthentications publickey\n\
    PasswordAuthentication no\n\
    KbdInteractiveAuthentication no\n\
' > /etc/ssh/ssh_config

USER runner
WORKDIR /home/runner
COPY run-ssh.sh /usr/local/bin/run-ssh
RUN chmod +x /usr/local/bin/run-ssh
ENTRYPOINT ["/usr/local/bin/run-ssh"]
