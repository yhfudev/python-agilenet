#!/bin/bash

# apt install telnet
# apt install expect
# apt install uuid-runtime # uuidgen

run_serial() {
  PARAM_SERIAL_PORT=$1
  shift
  PARAM_SERIAL_SPEED=$1
  shift
  PARAM_FN_BASHSCRIPT=$1
  shift

  FN_TMP=/tmp/ttyDump.txt

  stty -F ${PARAM_SERIAL_PORT} ${PARAM_SERIAL_SPEED} raw -echo   #CONFIGURE SERIAL PORT
  exec 3<${PARAM_SERIAL_PORT}             #REDIRECT SERIAL OUTPUT TO FD 3
    cat <&3 > ${FN_TMP} &                 #REDIRECT SERIAL OUTPUT TO FILE
    PID=$!                                #SAVE PID TO KILL CAT
      cat "${PARAM_FN_BASHSCRIPT}" > ${PARAM_SERIAL_PORT} #SEND COMMAND STRING TO SERIAL PORT
      sleep 0.2s                          #WAIT FOR RESPONSE
    kill $PID                             #KILL CAT PROCESS
    wait $PID 2>/dev/null                 #SUPRESS "Terminated" output

  exec 3<&-                               #FREE FD 3
  cat ${FN_TMP}                           #DUMP CAPTURED DATA
}

run_ssh() {
  PARAM_SSH_USER=$1
  shift
  PARAM_SSH_HOST=$1
  shift
  PARAM_FN_BASHSCRIPT=$1
  shift

  echo
  echo "Run remote ssh command from host ${PARAM_SSH_USER}@${PARAM_SSH_HOST} ..."
  ssh ${PARAM_SSH_USER}@${PARAM_SSH_HOST} 'bash -l' < "${PARAM_FN_BASHSCRIPT}"
}

# for local serial to net service
run_telnet() {
  PARAM_TELNET_HOST=$1
  shift
  PARAM_TELNET_PORT=$1
  shift
  PARAM_FN_BASHSCRIPT=$1
  shift
  cat "${PARAM_FN_BASHSCRIPT}" | telnet ${PARAM_TELNET_HOST} ${PARAM_TELNET_PORT}
}


ARG_CMD=$1
shift

case ${ARG_CMD} in

shutdown)
  FN_RUN="/tmp/bashscript-shutdown-$(uuidgen)"
  cat > "${FN_RUN}" <<EOF
shutdown -h now || reboot
EOF
  run_ssh $USER ant-k8s-03 "${FN_RUN}"
  run_ssh $USER ant-k8s-05 "${FN_RUN}"
  rm -f "${FN_RUN}"
  FN_RUN="/tmp/bashscript-reload-$(uuidgen)"
  cat > "${FN_RUN}" <<EOF
reload
EOF

  #run_serial "/dev/ttyUSB0" 115200 "${FN_RUN}" # OpenWrt
  #run_serial "/dev/ttyUSB1" 9600   "${FN_RUN}" # Cisco C2960 WS-C2960-8TC-L
  #run_serial "/dev/ttyUSB2" 9600   "${FN_RUN}" # Dell PowerConnect 5324
  #run_serial "/dev/ttyACM0" 90600  "${FN_RUN}" # HP/Aruba J9727A 2920-24G-PoE+ Switch (speedsense,default 9600)
  rm -f "${FN_RUN}"
  ;;

svrstart)
  socat TCP-LISTEN:6000,fork,reuseaddr  FILE:/dev/ttyRT1ow,b115200,raw,echo=0 & # OpenWrt
  socat TCP-LISTEN:6001,fork,reuseaddr FILE:/dev/ttySW1cisco,b9600,raw,echo=0 & # Cisco C2960 WS-C2960-8TC-L
  socat TCP-LISTEN:6002,fork,reuseaddr  FILE:/dev/ttySW2dell,b9600,raw,echo=0 & # Dell PowerConnect 5324
  socat TCP-LISTEN:6003,fork,reuseaddr FILE:/dev/ttySW3aruba,b9600,raw,echo=0 & # HP/Aruba J9727A 2920-24G-PoE+ Switch (speedsense,default 9600)
  ;;

svrstop)
  ps -ef | grep "socat TCP-LISTEN:600" | awk '{print $2}' | xargs -n 1 kill -9
  ;;

pingdns)
  FN_RUN="/tmp/bashscript-pingdns-$(uuidgen)"
  cat > "${FN_RUN}" <<EOF
ping -c 5 8.8.8.8
EOF
  run_ssh $USER ant-k8s-03 "${FN_RUN}"
  run_ssh $USER ant-k8s-05 "${FN_RUN}"
  rm -f "${FN_RUN}"
  ;;

showip)
  FN_RUN="/tmp/bashscript-showip-$(uuidgen)"
  cat > "${FN_RUN}" <<EOF
ip a
EOF
  run_ssh $USER ant-k8s-03 "${FN_RUN}"
  run_ssh $USER ant-k8s-05 "${FN_RUN}"
  rm -f "${FN_RUN}"
  ;;

cmd)
  FN_RUN="/tmp/bashscript-showip-$(uuidgen)"
  cat > "${FN_RUN}" <<EOF
$@
EOF
  run_ssh $USER ant-k8s-03 "${FN_RUN}"
  run_ssh $USER ant-k8s-05 "${FN_RUN}"
  rm -f "${FN_RUN}"
  ;;


*)
  echo "unknown command: ${ARG_CMD}"
  exit 1

esac


exit 0

expect << EOF
spawn telnet home-pogoplug-v3-1 6003
send "\r\n"
expect -re ".*#"
send "show ver\r"
expect -re "Active Boot ROM:"
send "exit\r"
EOF





