function serial_bench(port, seconds)
% Standalone physical I/O inspection; NOT the complete live security server.
% Example: serial_bench("COM4",30). Close Arduino Serial Monitor first.
if nargin<2,seconds=30;end
s=serialport(port,115200,'Timeout',.2);configureTerminator(s,'LF');flush(s);
cleanup=onCleanup(@() delete(s));
t=tic;heartbeat=-1;
while toc(t)<seconds
    if toc(t)-heartbeat>=.5,writeline(s,'HB');heartbeat=toc(t);end
    if s.NumBytesAvailable>0
        try
            line=readline(s);disp(line);
        catch e
            warning('serial_bench:read','%s',e.message);
        end
    end
    pause(.01);
end
end
