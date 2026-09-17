function verify_room_quality
% Check the frozen room model on every independent held-out clip.
s = load('results/detection-quality/room_reference.mat');
model = struct('center',s.center,'scale',s.scale,'threshold',s.threshold);
largest = 0;
for k = 1:size(s.x,1)
    f = struct('x',squeeze(s.x(k,:,:)),'valid',logical(s.valid(k,:).'));
    [score,flag] = audio_detect(f,model);
    largest = max(largest,max(abs(score-s.scores(k,:).')));
    assert(isequal(flag,logical(s.flags(k,:).')), 'Room audio flags differ');
end
assert(largest < 1e-10, 'Room audio scores differ');
fprintf('ROOM_MATLAB clips=%d max_score_error=%.17g flags=identical\n',size(s.x,1),largest);
end
