function [score, flag] = audio_detect(f, model)
z=(f.x-model.center)./model.scale;
score=sqrt(mean(min(z.^2,400),2));
raw=(score>model.threshold)&f.valid;
persistence=filter([1 1 1],1,double(raw))>=2;
extreme=(score>2*model.threshold)&(f.x(:,8)>log(8))&f.valid;
flag=(persistence|extreme)&f.valid;
end
