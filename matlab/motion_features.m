function out = motion_features(previous, current)
% Both brightness gain and offset are fitted; local changes are trimmed out.
a=double(previous(:));b=double(current(:));
health=mean(b)<4 || std(b,1)<1 || mean(b>=254)>.85;
out=struct('motion',false,'fraction',0,'naive',mean(abs(b-a)>12),...
    'health',health,'gain',1,'offset',0);
if health, return; end
keep=a>5 & a<250 & b>5 & b<250;gain=1;offset=0;
if sum(keep)>=100
    for k=1:3
        aa=a(keep);bb=b(keep);variance=mean((aa-mean(aa)).^2);
        gain=min(4,max(.25,mean((aa-mean(aa)).*(bb-mean(bb)))/max(variance,1)));
        offset=median(bb-gain*aa);residual=abs(b-(gain*a+offset));
        values=sort(residual);pos=1+.85*(numel(values)-1);
        cutoff=values(floor(pos))+(pos-floor(pos))*(values(ceil(pos))-values(floor(pos)));
        keep=residual<=cutoff & a>5 & a<250 & b>5 & b<250;
        if sum(keep)<100,break;end
    end
end
out.fraction=mean(abs(b-(gain*a+offset))>12);out.motion=out.fraction>.018;
out.gain=gain;out.offset=offset;
end
