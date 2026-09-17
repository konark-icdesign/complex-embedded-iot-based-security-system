function [s, output] = fusion_step(s, t, evidence, health)
% Evidence order [A V P M U]. No class labels or scenario names enter here.
if isempty(s)
    s=struct('last',-1e9*ones(1,5),'state',0,'changed',0,...
        'lastYellow',-1e9,'lastActivity',-1e9,'lastTime',-1,'alerts',0);
end
assert(t>=s.lastTime,'Capture times must be monotonic');s.lastTime=t;
s.last(logical(evidence))=t;
present=t-s.last<=4.0; score=sum([1.5 3 2 2 2].*present);
physical=sum(present(3:5));
rule=(present(2)&&physical>=1)||physical>=3||(present(1)&&physical>=2);
confirmed=rule&&score>=5;suspicious=any(present)||health;
if any(present),s.lastActivity=t;end
if suspicious,s.lastYellow=t;end
entered=false;
if confirmed
    if s.state==0
        s.state=1;s.changed=t;
    elseif s.state~=2
        s.state=2;s.changed=t;s.alerts=s.alerts+1;entered=true;
    end
elseif s.state==2
    if t-s.changed>=6 && t-s.lastActivity>=3,s.state=double(health);s.changed=t;end
elseif suspicious
    if s.state~=1,s.state=1;s.changed=t;end
elseif t-s.lastYellow>=3
    s.state=0;
end
output=struct('state',s.state,'score',score,'entered',entered);
end
