import { DoorOpen, Fan, Lightbulb, ShieldAlert, UsersRound, Waves, Wind } from 'lucide-react';
import { isActiveAlert, isLit, isOpenDoor } from '../selectors';
import type { HomeState } from '../types';
import type { ActiveListRequest } from './ActiveDevicesDialog';

/** onOpen：点亮灯、空调、地暖标签打开对应列表（可一键关闭）。 */
export function HomeStatusSummary({ home, onOpen }: { home: HomeState; onOpen: (request: ActiveListRequest) => void }) {
  const alerts = home.devices.filter(isActiveAlert).length;
  const openDoors = home.devices.filter(isOpenDoor);
  const peopleHome = home.people.filter((person) => person.status === 'home');
  const lit = home.devices.filter(isLit).length;
  const runningAirConditioners = home.devices.filter((device) => device.kind === 'climate' && device.available && device.on).length;
  const runningFloorHeatings = home.devices.filter((device) => device.kind === 'heating' && device.available && device.on).length;
  const runningFans = home.devices.filter((device) => device.kind === 'fan' && device.available && device.on).length;

  return (
    <div className="status-row" aria-label="家庭状态">
      {alerts > 0 && <span className="status-pill status-pill--alert"><ShieldAlert size={15} />{alerts} 项安全告警</span>}
      {peopleHome.length > 0 && <span className="status-pill status-pill--home"><UsersRound size={15} />{peopleHome.map((person) => person.name).join('、')}在家</span>}
      {lit > 0 && <button type="button" className="status-pill status-pill--light status-pill--button" onClick={() => onOpen({ kind: 'light' })}><Lightbulb size={15} />{lit} 盏灯亮</button>}
      {runningAirConditioners > 0 && <button type="button" className="status-pill status-pill--cool status-pill--button" onClick={() => onOpen({ kind: 'climate' })}><Wind size={15} />{runningAirConditioners} 台空调开启</button>}
      {openDoors.length > 0 && <span className="status-pill"><DoorOpen size={15} />{openDoors.length <= 2 ? `${openDoors.map((device) => device.name).join('、')}已打开` : `${openDoors.length} 处门窗打开`}</span>}
      {runningFloorHeatings > 0 && <button type="button" className="status-pill status-pill--heat status-pill--button" onClick={() => onOpen({ kind: 'heating' })}><Waves size={15} />{runningFloorHeatings} 处制热已开启</button>}
      {runningFans > 0 && <button type="button" className="status-pill status-pill--cool status-pill--button" onClick={() => onOpen({ kind: 'fan' })}><Fan size={15} />{runningFans} 台风扇开启</button>}
    </div>
  );
}
