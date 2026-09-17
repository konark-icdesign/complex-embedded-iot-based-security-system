function model = fit_baseline(training, calibration)
floors=[.025 .025 .025 .025 .02 .08 .025 .10 .10];
model.center=median(training,1);
model.scale=max(1.4826*median(abs(training-model.center),1),floors);
z=(calibration-model.center)./model.scale;
scores=sort(sqrt(mean(min(z.^2,400),2)));
% Explicit linear quantile matches numpy.quantile(method='linear').
position=1+.995*(numel(scores)-1);
q=scores(floor(position))+(position-floor(position))*(scores(ceil(position))-scores(floor(position)));
model.threshold=max(3.5,1.2*q);
end
