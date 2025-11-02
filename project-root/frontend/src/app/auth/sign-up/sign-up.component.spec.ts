import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SingUp } from './sing-up';

describe('SingUp', () => {
  let component: SingUp;
  let fixture: ComponentFixture<SingUp>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SingUp]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SingUp);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
