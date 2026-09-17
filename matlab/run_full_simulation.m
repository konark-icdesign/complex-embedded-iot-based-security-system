function run_full_simulation()
% MATLAB reference calculations and fusion replay. Uses base MATLAB.
% Checks audio/image kernels and replays the central fusion traces.
% MATLAB execution and physical I/O tests are still pending.
root=fileparts(fileparts(mfilename('fullpath')));addpath(fullfile(root,'matlab'));
fixture=load(fullfile(root,'fixtures','matlab_reference.mat'));
outdir=fullfile(root,'results','matlab');if ~exist(outdir,'dir'),mkdir(outdir);end
diary(fullfile(outdir,'execution_log.txt'));cleanup=onCleanup(@() diary('off'));
fprintf('MATLAB execution: %s\n',version);
f=audio_features(fixture.audio,fixture.fs);
featureError=max(abs(f.x-fixture.expected_features),[],'all');
assert(featureError<1e-8,'Feature parity failed');
assert(max(abs(f.t-fixture.expected_times(:)))<1e-10,'End-time parity failed');
models=struct;
for name={'dry','rain'}
    mode=name{1};training=[];calibration=[];
    wave=fixture.(['train_' mode]);
    for k=1:size(wave,2),ff=audio_features(wave(:,k),fixture.fs);training=[training;ff.x];end %#ok<AGROW>
    wave=fixture.(['cal_' mode]);
    for k=1:size(wave,2),ff=audio_features(wave(:,k),fixture.fs);calibration=[calibration;ff.x];end %#ok<AGROW>
    models.(mode)=fit_baseline(training,calibration);
    assert(max(abs(models.(mode).center-fixture.(['center_' mode])))<1e-8);
    assert(max(abs(models.(mode).scale-fixture.(['scale_' mode])))<1e-8);
    assert(abs(models.(mode).threshold-fixture.(['threshold_' mode]))<1e-8);
end
[score,flag]=audio_detect(f,models.dry);
figure('Visible','off');plot(f.t,score);hold on;yline(models.dry.threshold,'--');
xlabel('Time (s)');ylabel('Deviation score');title('MATLAB DSP on synthetic raw audio');
saveas(gcf,fullfile(outdir,'audio.png'));close(gcf);
% Lighting test, including local foreground and additive global change.
im=double(fixture.frames(:,:,1));light=motion_features(im,im+60);
assert(light.fraction<.001);
local=im;local(31:80,41:70)=local(31:80,41:70)+60;
person=motion_features(im,local);assert(abs(person.fraction-1500/19200)<.001);
motion=zeros(size(fixture.frames,3),1);
for k=2:numel(motion)
    z=motion_features(fixture.frames(:,:,k-1),fixture.frames(:,:,k));motion(k)=z.fraction;
end
figure('Visible','off');plot(fixture.frame_times,motion);xlabel('Time (s)');ylabel('Changed image fraction');
saveas(gcf,fullfile(outdir,'motion.png'));close(gcf);
files=dir(fullfile(root,'results','traces','*.csv'));assert(~isempty(files),'Run Python fixture generation first');
rows=cell(numel(files),3);
for k=1:numel(files)
    data=readtable(fullfile(files(k).folder,files(k).name));s=[];predicted=zeros(height(data),1);
    for j=1:height(data)
        if ~data.server(j),predicted(j)=-1;continue;end
        [s,o]=fusion_step(s,data.t(j),[data.A(j),data.V(j),data.P(j),data.M(j),data.U(j)],logical(data.health(j)));
        predicted(j)=o.state;
        assert(abs(o.score-data.score(j))<1e-8,'Fusion score mismatch');
    end
    mismatch=sum(predicted~=data.state);assert(mismatch==0,'Fusion state mismatch');
    rows(k,:)={files(k).name,mismatch,any(predicted==2)};
end
writetable(cell2table(rows,'VariableNames',{'scenario','mismatches','centralRed'}),fullfile(outdir,'fusion_parity.csv'));
fprintf('PASS raw DSP, baseline fit, lighting kernels and %d fusion trace replays.\n',numel(files));
fprintf('Max DSP feature discrepancy: %.3g; anomalous windows: %d\n',featureError,sum(flag));
fprintf('Physical microphone, camera, serial and Arduino tests remain separate.\n');
save(fullfile(outdir,'verified_models.mat'),'models');
end
