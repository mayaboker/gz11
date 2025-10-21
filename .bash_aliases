source /usr/share/gazebo/setup.sh
export GAZEBO_MODEL_PATH=/workspace/src/ardupilot_gazebo/models:$GAZEBO_MODEL_PATH
export GAZEBO_RESOURCE_PATH=/workspace/src/ardupilot_gazebo/worlds:$GAZEBO_RESOURCE_PATH
export LD_LIBRARY_PATH=/workspace/src/ardupilot_gazebo/build:$LD_LIBRARY_PATH

alias a=alias
alias h=history
alias j=jobs
alias d=date
alias rm='rm -i'
alias ver='lsb_release -a'
alias path='(IFS=:;ls -1d $PATH |  nl)'

