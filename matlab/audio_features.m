function f = audio_features(audio, fs)
% Base MATLAB only. Symmetric Hann, one-sided power, causal END timestamps.
% Implemented independently from the Python numerical reference.
N=2048; hop=1024; x=double(audio(:));
assert(numel(x)>=N && all(isfinite(x)), 'Need finite mono audio');
count=floor((numel(x)-N)/hop)+1;
frames=zeros(count,N);
for k=1:count
    frames(k,:)=x((k-1)*hop+(1:N)).';
end
clipped=mean(abs(frames)>=.999,2)>.01;
frames=frames-mean(frames,2);
rmsValue=sqrt(mean(frames.^2,2));
window=.5-.5*cos(2*pi*(0:N-1)/(N-1));
ft=fft(frames.*window,[],2);power=abs(ft(:,1:N/2+1)).^2;
power(:,2:end-1)=2*power(:,2:end-1);
p=power./max(sum(power,2),1e-30);
freq=(0:N/2)*fs/N;
bands=[0 250;250 1000;1000 4000;4000 fs/2+1];
F=zeros(count,9);
for j=1:4
    F(:,j)=sum(p(:,freq>=bands(j,1) & freq<bands(j,2)),2);
end
F(:,5)=sum(p.*freq,2)/(fs/2);
F(:,6)=exp(mean(log(max(p,1e-30)),2))*size(p,2);
F(:,7)=mean(frames(:,2:end).*frames(:,1:end-1)<0,2);
F(:,8)=log(max(max(abs(frames),[],2)./max(rmsValue,1e-15),1));
sub=zeros(count,8);
for j=1:8
    sub(:,j)=sqrt(mean(frames(:,(j-1)*(N/8)+(1:N/8)).^2,2));
end
F(:,9)=std(sub,1,2)./max(mean(sub,2),1e-15);
f=struct('x',F,'t',((0:count-1)'*hop+N)/fs,'rms',rmsValue,...
    'dbfs',20*log10(max(rmsValue,1e-15)),'valid',rmsValue>1e-7 & ~clipped);
end
